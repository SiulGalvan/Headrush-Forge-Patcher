#!/bin/sh
# mx5forge diagnostic sampler (not part of MX-Edit): started by mx5bridge-usb.sh when USB audio starts.
# Every 2 s for ~2 minutes it writes one CSV line to $OUT with
#   t,total,c0..cN   busy % of all cores / of each core (from /proc/stat deltas)
#   evil             CPU % (of one core) of all Evil threads, usbirq = the USB interrupt kernel thread, ksoft = ksoftirqd
#   irqs             USB interrupts per second
#   est,err          estimate of the total from the thread figures and its error (see README of the tool)
#   top              the 3 busiest Evil threads (name=% of one core)
# All values are in tenths of a percent (123 = 12.3 %). Pure sh, no forks inside the loop except `sleep`.
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
		read -r c < "$p/comm" 2>/dev/null || continue
		case "$c" in $1) echo "${p#/proc/}"; return;; esac
	done
}
EV=$(find_pid "$EVNAME")
IRQP=$(find_pid "irq/*ff580000*")
KSP=$(for p in /proc/[0-9]*; do read -r c < "$p/comm" 2>/dev/null; case "$c" in ksoftirqd/*) printf '%s ' "${p#/proc/}";; esac; done)
[ -n "$EV" ] || exit 0

ticks() {      # file -> utime+stime of a /proc/<pid>[/task/<tid>]/stat, comm in $comm
	{ read -r _l < "$1"; } 2>/dev/null || { T=0; return; }
	_x=${_l#*(}; comm=${_x%)*}; _r=${_l##*) }
	set -- $_r
	T=$(( ${12} + ${13} ))
}
stat_read() {  # fills B_<cpu>, T_<cpu> (busy/total ticks) from /proc/stat
	while read -r n u ni s id io irq sirq st rest; do
		case "$n" in cpu|cpu[0-9]*)
			eval "B_$n=$((u+ni+s+irq+sirq)) T_$n=$((u+ni+s+id+io+irq+sirq+st))";;
		esac
	done < /proc/stat
}
usb_irqs() {   # sum of the per-CPU counters of the ff580000 line
	U=0
	while read -r n rest; do
		case "$rest" in *ff580000*) set -- $rest; U=$(( $1 + $2 + $3 + $4 )); break;; esac
	done < /proc/interrupts
}
NC=0; for d in /sys/devices/system/cpu/cpu[0-9]*; do NC=$((NC+1)); done
[ $NC -ge 1 ] || NC=1

{
	echo "# mx5forge probe: evil pid $EV, usb irq thread ${IRQP:-none}, ksoftirqd ${KSP:-none}, cores $NC, step ${STEP}s, tenths of %"
	echo "t,total,$(i=0; while [ $i -lt $NC ]; do printf 'c%d,' $i; i=$((i+1)); done)evil,usbirq,ksoft,irqs,est,err,top"
} > "$OUT"

stat_read; for n in cpu $(i=0; while [ $i -lt $NC ]; do printf 'cpu%d ' $i; i=$((i+1)); done); do eval "PB_$n=\$B_$n PT_$n=\$T_$n"; done
usb_irqs; PU=$U
for t in /proc/$EV/task/*; do ticks "$t/stat"; eval "P_${t##*/}=$T"; done
PIRQ=0; [ -n "$IRQP" ] && { ticks /proc/$IRQP/stat; PIRQ=$T; }
PKS=0; for p in $KSP; do ticks /proc/$p/stat; PKS=$((PKS+T)); done

i=0
while [ $i -lt $N_SAMPLES ]; do
	sleep $STEP
	i=$((i+1))
	stat_read
	E=$((T_cpu0 - PT_cpu0)); [ $E -gt 0 ] || E=1
	line="$((i*STEP))"
	DB=$((B_cpu - PB_cpu)); DT=$((T_cpu - PT_cpu)); [ $DT -gt 0 ] || DT=1
	total=$((DB * 1000 / DT)); line="$line,$total"
	for n in $(j=0; while [ $j -lt $NC ]; do printf 'cpu%d ' $j; j=$((j+1)); done); do
		eval "b=\$B_$n pb=\$PB_$n tt=\$T_$n ptt=\$PT_$n"
		dt=$((tt - ptt)); [ $dt -gt 0 ] || dt=1
		line="$line,$(( (b - pb) * 1000 / dt ))"
	done
	for n in cpu $(j=0; while [ $j -lt $NC ]; do printf 'cpu%d ' $j; j=$((j+1)); done); do eval "PB_$n=\$B_$n PT_$n=\$T_$n"; done
	# Evil threads
	sum=0; top1=0; top2=0; top3=0; n1=; n2=; n3=
	for t in /proc/$EV/task/*; do
		tid=${t##*/}; ticks "$t/stat"
		eval "p=\${P_$tid:-$T}"; eval "P_$tid=$T"
		d=$(( (T - p) * 1000 / E ))
		sum=$((sum + d))
		if [ $d -gt $top1 ]; then top3=$top2; n3=$n2; top2=$top1; n2=$n1; top1=$d; n1="$comm"
		elif [ $d -gt $top2 ]; then top3=$top2; n3=$n2; top2=$d; n2="$comm"
		elif [ $d -gt $top3 ]; then top3=$d; n3="$comm"; fi
	done
	irq=0; [ -n "$IRQP" ] && { ticks /proc/$IRQP/stat; irq=$(( (T - PIRQ) * 1000 / E )); PIRQ=$T; }
	ks=0; kt=0; for p in $KSP; do ticks /proc/$p/stat; kt=$((kt + T)); done; ks=$(( (kt - PKS) * 1000 / E )); PKS=$kt
	usb_irqs; irqs=$(( (U - PU) / STEP )); PU=$U
	# estimate of the total from the thread figures: every figure is "% of one core", the total is of NC cores.
	# Evil + the USB irq thread + ksoftirqd; the rest of the system (daemons, kernel) is the residual.
	est=$(( (sum + irq + ks) / NC )); err=$(( total - est ))
	echo "$line,$sum,$irq,$ks,$irqs,$est,$err,$n1=$top1 $n2=$top2 $n3=$top3" >> "$OUT"
done
{
	echo "=== gadget"; ls /sys/kernel/config/usb_gadget/g1/functions /sys/kernel/config/usb_gadget/g1/configs/c.1 2>&1
	echo "=== interrupts"; grep -i -E "usb|dwc|ff58|ff54" /proc/interrupts
	echo "=== cpu affinity of the USB irq"; cat /proc/irq/*/smp_affinity_list 2>/dev/null | sort | uniq -c
	echo "=== dmesg"; dmesg | tail -n 40
} > "$INFO" 2>&1
sync
