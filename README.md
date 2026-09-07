Part 1 writeup
==============

Files
-----
  opcodes.c           Part A/B source
  vector.c            Part D loops + test driver
  script.py           opcode / basic-block counter (parses instructions)
  extract_passes.py   Part C: transformation-pass lists from opt dumps
  pass/               strength-reduce: integer mul by 2^k -> shl
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

  python3 extract_passes.py --available available-passes.txt \
    passes.O0.txt passes.O1.txt passes.O2.txt passes.O3.txt --ordered --latex

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

Strength-reduce pass (mul by 2^k -> shl)
----------------------------------------
  export PATH="/opt/homebrew/opt/llvm@18/bin:$PATH"
  cmake -S pass -B pass/build \
    -DLLVM_DIR="$(llvm-config --cmakedir)" \
    -DCMAKE_CXX_COMPILER="$(llvm-config --bindir)/clang++"
  cmake --build pass/build

  clang -O0 -Xclang -disable-O0-optnone -S -emit-llvm \
    pass/tests/mul_shl.c -o /tmp/mul_shl.O0.ll
  opt -S -passes=mem2reg /tmp/mul_shl.O0.ll -o /tmp/mul_shl.mem2reg.ll
  opt -load-pass-plugin=pass/build/StrengthReducePass.dylib \
      -passes=strength-reduce -S /tmp/mul_shl.mem2reg.ll

On Linux the plugin is StrengthReducePass.so instead of .dylib.
The pass rewrites only integer mul by a positive power of two (k >= 1).
It leaves mul by 7, -8, a variable, and existing shl alone.

Report
------
  pdflatex main.tex
  pdflatex main.tex
