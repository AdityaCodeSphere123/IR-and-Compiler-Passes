Machines
--------
Parts A and B: Homebrew LLVM 23.1.0, Apple M3.

Parts C and D: Homebrew LLVM 18.1.8, Apple M1. 


Parts A and B
-------------
    clang -O0 -Xclang -disable-O0-optnone -S -emit-llvm opcodes.c -o opcodes.O0.ll
    opt -S -passes=mem2reg opcodes.O0.ll -o opcodes.mem2reg.ll
    opt -S -passes='mem2reg,simplifycfg' opcodes.O0.ll -o opcodes.canonical.ll

Then O1, O2, O3:

    clang -O1 -S -emit-llvm opcodes.c -o opcodes.O1.ll
    clang -O2 -S -emit-llvm opcodes.c -o opcodes.O2.ll
    clang -O3 -S -emit-llvm opcodes.c -o opcodes.O3.ll

Count blocks and opcodes on those four files:

    python3 script.py opcodes.O0.ll opcodes.O1.ll opcodes.O2.ll opcodes.O3.ll


Part C
------
Check the version, list available passes, then dump each default pipeline
(needs opcodes.O0.ll from above):

    opt --version
    opt --print-passes > available-passes.txt
    for level in O0 O1 O2 O3; do
      opt -passes="default<${level}>" -print-pipeline-passes \
          -disable-output opcodes.O0.ll > passes.${level}.txt
    done


Part D
------
    clang -O3 -fno-vectorize -fno-slp-vectorize -S -emit-llvm vector.c -o vector.scalar.ll
    clang -O3 -march=native -Rpass=loop-vectorize -Rpass-missed=loop-vectorize \
          -Rpass-analysis=loop-vectorize -S -emit-llvm vector.c -o vector.vector.ll \
          2> vector.remarks.txt

Same flags, but binaries this time. Both should print the same five lines:

    clang -O3 -fno-vectorize -fno-slp-vectorize vector.c -o vector.scalar
    clang -O3 -march=native vector.c -o vector.vector
    ./vector.scalar
    ./vector.vector
