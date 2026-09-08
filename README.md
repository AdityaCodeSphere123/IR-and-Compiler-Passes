Lab 2 (COL729)
==============

What is in this folder
----------------------
opcodes.c     three noinline functions for Parts A and B
vector.c      four noinline kernels plus main for Part D
script.py     counts blocks and opcodes in a .ll file
report.pdf    the write-up

Leave .ll dumps, pass lists, remarks, and binaries out of the archive.

We used Homebrew clang/opt 18.1.8 on an arm64 Mac. Put that llvm@18 bin
directory first on PATH so clang and opt are the same compiler. Vector
width in the report is 4 (NEON 128-bit lanes).

    export PATH="/opt/homebrew/opt/llvm@18/bin:$PATH"


opcodes.c
---------
f1 writes through a struct (scalar, 2D field, pointer) with a runtime
index. f2 is the short loop with int/float compares. f3 has the switch,
the call, the ternary, and the casts.

Unoptimised IR and the two named cleanups from the report:

    clang -O0 -Xclang -disable-O0-optnone -S -emit-llvm opcodes.c -o opcodes.O0.ll
    opt -S -passes=mem2reg opcodes.O0.ll -o opcodes.mem2reg.ll
    opt -S -passes='mem2reg,simplifycfg' opcodes.O0.ll -o opcodes.canonical.ll

Then the three opt levels:

    clang -O1 -S -emit-llvm opcodes.c -o opcodes.O1.ll
    clang -O2 -S -emit-llvm opcodes.c -o opcodes.O2.ll
    clang -O3 -S -emit-llvm opcodes.c -o opcodes.O3.ll

Feed those four files to script.py. It walks define bodies, ignores
comments, and prints one row per function: block count plus each opcode
it saw.

    python3 script.py opcodes.O0.ll opcodes.O1.ll opcodes.O2.ll opcodes.O3.ll


Pipelines (Part C)
------------------
There is no pipeline script. Print opt --version, dump the default
pipeline at each level, and dump the pass catalogue. The ordered lists
and the short notes live in report.pdf.

    opt --version
    opt --print-passes > available-passes.txt
    for level in O0 O1 O2 O3; do
      opt -passes="default<${level}>" -print-pipeline-passes \
          -disable-output opcodes.O0.ll > passes.${level}.txt
    done

When reading the dump, skip pass-manager wrappers (the names with
parentheses), skip analyses / require / invalidate / remarks, and keep
repeated transform names in the order they appear.


vector.c
--------
Length is an argument. Arrays that must not overlap are restrict.

    f1  c[i] = a[i]*alph + b[i]          (floats)
    f2  integer dot product
    f3  if guess[i] then a[i] else b[i]
    f4  interleave into c[2*i], c[2*i+1] (only so shufflevector shows up)

main fills buffers with float_fill / int_fill, runs all four kernels,
and prints n plus checksum for 7, 16, 1023, 1024, 2048. Two of those
are >= 1024; 7 and 1023 are not a multiple of 4.

Scalar IR (both vectorisers off), then native vector IR + remarks:

    clang -O3 -fno-vectorize -fno-slp-vectorize -S -emit-llvm vector.c -o vector.scalar.ll
    clang -O3 -march=native -Rpass=loop-vectorize -Rpass-missed=loop-vectorize \
          -S -emit-llvm vector.c -o vector.vector.ll 2> vector.remarks.txt

Same flags without -S to get two binaries. Both should print the same
five lines:

    clang -O3 -fno-vectorize -fno-slp-vectorize vector.c -o vector.scalar
    clang -O3 -march=native vector.c -o vector.vector
    ./vector.scalar
    ./vector.vector
