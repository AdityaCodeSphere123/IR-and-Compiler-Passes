/* Cases the pass should rewrite: mul by 2, 8, 16 (powers of two, k >= 1). */
int mul2(int x) { return x * 2; }
int mul8(int x) { return x * 8; }
int mul16_commuted(int x) { return 16 * x; }

/* Leave these alone: not a positive power of two, or already a shift. */
int mul7(int x) { return x * 7; }
int mul_neg8(int x) { return x * -8; }
int mul_var(int x, int y) { return x * y; }
int already_shl(int x) { return x << 3; }
