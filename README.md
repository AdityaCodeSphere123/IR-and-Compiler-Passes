Part 1 writeup
==============

Files
-----
  opcodes.c           Part A/B source
  vector.c            Part D loops + test driver
  script.py           opcode / basic-block counter (parses instructions)
  main.tex            report
  cfg.png             CFG of the loop function
  opcode_table.png    opcode-count table
  main.pdf            compiled report

LLVM version / target
---------------------
Use the same install for clang and opt. This report used Homebrew LLVM 18.1.8
on macOS arm64 (Apple Silicon), NEON 128-bit:

  export PATH="/opt/homebrew/opt/llvm@18/bin:$PATH"
  opt --version

Part A / B IR
-------------
  clang -O0 -Xclang -disable-O0-optnone -S -emit-llvm opcodes.c -o opcodes.O0.ll
  opt -S -passes=mem2reg opcodes.O0.ll -o opcodes.mem2reg.ll
  opt -S -passes='mem2reg,simplifycfg' opcodes.O0.ll -o opcodes.canonical.ll
  clang -O1 -S -emit-llvm opcodes.c -o opcodes.O1.ll
  clang -O2 -S -emit-llvm opcodes.c -o opcodes.O2.ll
  clang -O3 -S -emit-llvm opcodes.c -o opcodes.O3.ll

  python3 script.py opcodes.O0.ll opcodes.O1.ll opcodes.O2.ll opcodes.O3.ll
  python3 script.py --latex opcodes.O0.ll opcodes.O1.ll opcodes.O2.ll opcodes.O3.ll

Part C pipelines
----------------
  for level in O0 O1 O2 O3; do
    opt -passes="default<${level}>" -print-pipeline-passes \
      -disable-output opcodes.O0.ll > passes.${level}.txt
  done
  opt --print-passes > available-passes.txt

Part D vectorisation
--------------------
  clang -O3 -fno-vectorize -fno-slp-vectorize -S -emit-llvm vector.c -o vector.scalar.ll
  clang -O3 -march=native -Rpass=loop-vectorize -Rpass-missed=loop-vectorize \
    -S -emit-llvm vector.c -o vector.vector.ll 2> vector.remarks.txt

  clang -O3 -fno-vectorize -fno-slp-vectorize vector.c -o vector.scalar
  clang -O3 -march=native vector.c -o vector.vector
  ./vector.scalar
  ./vector.vector

Do not submit the generated .ll / .txt / binary dumps.

Report
------
  pdflatex main.tex
