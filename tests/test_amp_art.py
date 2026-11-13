import unittest

from PIL import Image

from mx5forge.art import amp


class Badge(unittest.TestCase):
    def test_digit_is_cut_out_and_drawn_inside_the_icon(self):
        base = Image.new("RGBA", (290, 119), (30, 30, 30, 255))
        second = base.copy()
        for x in range(250, 262):
            for y in range(35, 55):
                second.putpixel((x, y), (255, 255, 255, 255))
        digit = amp.digit_from_stock(base, second)
        self.assertEqual(digit.size, (12, 20))
        icon = Image.new("RGBA", (290, 119), (0, 0, 0, 0))
        for x in range(65, 225):
            for y in range(13, 103):
                icon.putpixel((x, y), (0, 200, 180, 255))
        out = amp.with_badge(icon, digit)
        self.assertEqual(out.getpixel((200, 30)), (255, 255, 255, 255))     # inside the icon, top right
        self.assertEqual(out.getpixel((10, 10))[3], 0)                      # transparent margin untouched


if __name__ == "__main__":
    unittest.main()
