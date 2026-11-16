import unittest

from ps1bench.emulator import parse_output

SAMPLE = (
    "Loading memory card C:\\x\\memcard1.mcd\r\n"
    "PCSX-Redux Lua Console \r\n"
    "BIOS Trace1: 0x07\r\n"
    "Hijacked shell, loading hello.elf...\r\n"
    "Successful: new PC = 80010000...\r\n"
    "BENCH_SHELL=18175196 \r\n"
    "hello from the PS1\r\n"
    "  indented line  \r\n"
    "BENCH_CYCLES=18273719 \r\n"
)


class ParseOutputTest(unittest.TestCase):
    def test_program_output_follows_the_loader_line(self):
        # BENCH_SHELL is printed after the loader line; it is not output.
        out = parse_output(SAMPLE)
        self.assertEqual(out.stdout, "hello from the PS1\n  indented line\n")

    def test_cycles_are_counted_from_the_shell(self):
        out = parse_output(SAMPLE)
        self.assertEqual(out.cycles, 18273719 - 18175196)

    def test_output_ends_at_the_quit_marker(self):
        out = parse_output(SAMPLE + "emulator shutdown noise\r\n")
        self.assertEqual(out.stdout, "hello from the PS1\n  indented line\n")

    def test_missing_markers_give_no_cycles(self):
        out = parse_output("Successful: new PC = 80010000...\nhi\n")
        self.assertIsNone(out.cycles)
        self.assertEqual(out.stdout, "hi\n")

    def test_program_that_never_loaded_has_no_output(self):
        out = parse_output("BIOS Trace1: 0x07\nBENCH_CYCLES=5\n")
        self.assertEqual(out.stdout, "")
        self.assertFalse(out.loaded)


if __name__ == "__main__":
    unittest.main()
