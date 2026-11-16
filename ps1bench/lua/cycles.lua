-- Cycle probe for ps1bench, loaded with `pcsx-redux -dofile`.
-- Prints the CPU cycle counter when the BIOS reaches the shell (just before
-- the executable is loaded) and when the emulator quits (pcsx_exit()).
-- The listeners are globals so they are not garbage collected.
ps1bench_shell = PCSX.Events.createEventListener('ExecutionFlow::ShellReached', function()
  print(string.format('BENCH_SHELL=%d', tonumber(PCSX.getCPUCycles())))
end)
ps1bench_quit = PCSX.Events.createEventListener('Quitting', function()
  print(string.format('BENCH_CYCLES=%d', tonumber(PCSX.getCPUCycles())))
end)
