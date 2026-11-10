#!/bin/sh
# mx5forge diagnostic sampler (not part of MX-Edit): started by mx5bridge-usb.sh when USB audio starts.
# Every 2 s for ~2 minutes it writes one CSV line to $OUT (all values in tenths of a percent, 123 = 12.3 %):
#   t               seconds since the start of the sampler
#   total, c0..cN   busy % of all cores / of each core (/proc/stat deltas; interrupt time included)
#   evil            CPU of all Evil threads, oth = all other processes together (% of ONE core)
#   usbirq, ksoft   the USB interrupt kernel thread and ksoftirqd (already inside oth)
#   hirq            hard+soft interrupt time of the machine (% of all cores; not charged to any thread)
#   irqs            USB interrupts per second
#   est, err        est = (evil + oth) / cores, err = total - est
#   cost            milliseconds the sampler itself needed to scan /proc in that round (its own overhead)
#   top, otop       the 3 busiest Evil threads / other processes (name=% of one core)
# The interval used for every percentage is the real one, taken from /proc/uptime.
# Pure sh, no forks in the loop apart from `sleep`.
OUT=${PROBE_OUT:-/media/az01-internal/Evil/mx5bridge/probe.csv}
INFO=${OUT%.csv}_info.txt
EVNAME=${PROBE_EVIL:-Evil}
N_SAMPLES=${PROBE_N:-60}
STEP=${PROBE_STEP:-2}

mkdir /tmp/mx5probe.lock 2>/dev/null || exit 0
mkdir -p "${OUT%/*}" 2>/dev/null
trap 'rmdir /tmp/mx5probe.lock 2>/dev/null' EXIT

find_pid() {   # comm pattern -> pid (first match)
	for p in /proc/[0-9]*; do
		{ read -r c < "$p/comm"; } 2>/dev/null || continue
		case "$c" in $1) echo "${p#/proc/}"; return;; esac
	done
}
EV=$(find_pid "$EVNAME")
IRQP=$(find_pid "irq/*ff580000*")
[ -n "$EV" ] || exit 0
NC=0; for d in /sys/devices/system/cpu/cpu[0-9]*; do NC=$((NC+1)); done
[ $NC -ge 1 ] || NC=1
CPUS=$(j=0; while [ $j -lt $NC ]; do printf 'cpu%d ' $j; j=$((j+1)); done)

ticks() {      # stat file -> T = utime+stime, comm in $comm
	{ read -r _l < "$1"; } 2>/dev/null || { T=0; comm=; return; }
	_x=${_l#*(}; comm=${_x%)*}; _r=${_l##*) }
	set -- $_r
	T=$(( ${12} + ${13} ))
}
stat_read() {  # B_<cpu>/T_<cpu> = busy/total ticks, H_cpu = irq+softirq ticks of the whole machine
	while read -r n u ni s id io irq sirq st rest; do
		case "$n" in cpu|cpu[0-9]*)
			eval "B_$n=$((u+ni+s+irq+sirq)) T_$n=$((u+ni+s+id+io+irq+sirq+st))"
			[ "$n" = cpu ] && H_cpu=$((irq+sirq));;
		esac
	done < /proc/stat
}
uptime_cs() {  # centiseconds since boot in UP
	read -r _u _ < /proc/uptime
	_f=${_u#*.}; case "$_f" in 0?) _f=${_f#0};; esac
	UP=$(( ${_u%.*} * 100 + ${_f:-0} ))
}
usb_irqs() {   # sum of the per-CPU counters of the ff580000 line
	U=0
	while read -r n rest; do
		case "$rest" in *ff580000*) set -- $rest; U=$(( $1 + $2 + $3 + $4 )); break;; esac
	done < /proc/interrupts
}
top3() {       # $1 = value in tenths, $2 = name -> updates t1/t2/t3 and m1/m2/m3
	if [ "$1" -gt "$t1" ]; then t3=$t2; m3=$m2; t2=$t1; m2=$m1; t1=$1; m1=$2
	elif [ "$1" -gt "$t2" ]; then t3=$t2; m3=$m2; t2=$1; m2=$2
	elif [ "$1" -gt "$t3" ]; then t3=$1; m3=$2; fi
}

{
	echo "# mx5forge probe v3: evil pid $EV, usb irq thread ${IRQP:-none}, cores $NC, step ${STEP}s, tenths of %"
	echo "t,total,$(for c in $CPUS; do printf '%s,' "c${c#cpu}"; done)evil,oth,usbirq,ksoft,hirq,irqs,est,err,cost,top,otop"
} > "$OUT"

# first snapshot
stat_read; uptime_cs; PUP=$UP; T0=$UP; PH=$H_cpu
for n in cpu $CPUS; do eval "PB_$n=\$B_$n PT_$n=\$T_$n"; done
usb_irqs; PU=$U
for p in /proc/[0-9]*; do ticks "$p/stat"; eval "Q_${p#/proc/}=$T"; done
for t in /proc/$EV/task/*; do ticks "$t/stat"; eval "P_${t##*/}=$T"; done

i=0
while [ $i -lt $N_SAMPLES ]; do
	sleep $STEP
	i=$((i+1))
	uptime_cs; stat_read
	E=$((UP - PUP)); [ $E -gt 0 ] || E=1; PUP=$UP
	DT=$((T_cpu - PT_cpu)); [ $DT -gt 0 ] || DT=1
	line="$(( (UP - T0 + 50) / 100 )),$(( (B_cpu - PB_cpu) * 1000 / DT ))"
	for n in $CPUS; do
		eval "b=\$B_$n pb=\$PB_$n tt=\$T_$n ptt=\$PT_$n"
		dt=$((tt - ptt)); [ $dt -gt 0 ] || dt=1
		line="$line,$(( (b - pb) * 1000 / dt ))"
	done
	hirq=$(( (H_cpu - PH) * 1000 / DT )); PH=$H_cpu
	for n in cpu $CPUS; do eval "PB_$n=\$B_$n PT_$n=\$T_$n"; done
	# all processes: Evil is split into its threads, the others are listed per process
	evil=0; oth=0; usbirq=0; ksoft=0
	t1=0; t2=0; t3=0; m1=; m2=; m3=
	o1=0; o2=0; o3=0; q1=; q2=; q3=
	for p in /proc/[0-9]*; do
		pid=${p#/proc/}
		if [ "$pid" = "$EV" ]; then
			for t in /proc/$EV/task/*; do
				tid=${t##*/}; ticks "$t/stat"
				eval "o=\${P_$tid:-$T}; P_$tid=$T"
				d=$(( (T - o) * 1000 / E )); evil=$((evil + d))
				[ $d -gt 0 ] && top3 $d "$comm.$tid"
			done
			continue
		fi
		ticks "$p/stat"
		eval "o=\${Q_$pid:-$T}; Q_$pid=$T"
		d=$(( (T - o) * 1000 / E ))
		oth=$((oth + d))
		[ "$pid" = "$IRQP" ] && usbirq=$d
		case "$comm" in ksoftirqd/*) ksoft=$((ksoft + d));; esac
		if [ $d -gt 0 ]; then
			if [ $d -gt $o1 ]; then o3=$o2; q3=$q2; o2=$o1; q2=$q1; o1=$d; q1="$comm"
			elif [ $d -gt $o2 ]; then o3=$o2; q3=$q2; o2=$d; q2="$comm"
			elif [ $d -gt $o3 ]; then o3=$d; q3="$comm"; fi
		fi
	done
	usb_irqs; irqs=$(( (U - PU) * 100 / E )); PU=$U
	est=$(( (evil + oth) / NC )); tot=${line#*,}; tot=${tot%%,*}
	S0=$UP; uptime_cs; cost=$(( (UP - S0) * 10 ))   # ms between the interval end and the end of the scan
	echo "$line,$evil,$oth,$usbirq,$ksoft,$hirq,$irqs,$est,$((tot - est)),$cost,$m1=$t1 $m2=$t2 $m3=$t3,$q1=$o1 $q2=$o2 $q3=$o3" >> "$OUT"
done
{
	echo "=== gadget"; ls /sys/kernel/config/usb_gadget/g1/functions /sys/kernel/config/usb_gadget/g1/configs/c.1 2>&1
	echo "=== interrupts"; grep -i -E "usb|dwc|ff58|ff54" /proc/interrupts
	echo "=== irq affinity"; for f in /proc/irq/*/smp_affinity_list; do echo "$f $(cat $f)"; done 2>/dev/null | grep -E "/(4[5-8])/"
	echo "=== schedstat present: $([ -r /proc/schedstat ] && echo yes || echo no)"
	echo "=== dmesg"; dmesg | tail -n 40
} > "$INFO" 2>&1
sync
