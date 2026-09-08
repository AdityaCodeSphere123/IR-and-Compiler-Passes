#include <stdio.h>
#include <stdlib.h>

#define max_val 4096

// c = a * alph + b
void __attribute__((noinline)) f1(int n,float* restrict c,float* restrict a,float* restrict b,float alph){
	for(int i=0;i<n; i++){
		c[i]=a[i]*alph + b[i];
	}
}

// dot product of a nd b
int __attribute__((noinline)) f2(int n,int* restrict a, int* restrict b){
	int dot =0;
	for(int i = 0; i < n; i++){
		dot += a[i]*b[i];
	}
	return dot;
}

// c =a if guess[i] is true otherwise c=b
void __attribute__((noinline)) f3(int n,int* restrict c,int* restrict a, int* restrict b,int* restrict guess){
	for(int i = 0; i < n; i++){
		int a_val = a[i];
		int b_val =b[i];
		if (guess[i]){
			c[i]= a_val;
		} else{
			c[i] =b_val;
		}
	}
}

// c[2*i] = a[i], c[2*i + 1] = b[i]
void __attribute__((noinline)) f4(int n,int* restrict c,int* restrict a,int* restrict b){
	for(int i = 0; i < n; i++){
		c[2*i] = a[i];
		c[2*i + 1] = b[i];
	}
}

static void fill_float(float* p, int n, int seed){
	for(int i = 0; i < n; i++)
	{
		p[i] = (float)((seed + i * 3) % 17);
	}
}

static void fill_int(int* p, int n, int seed)
{
	for(int i = 0; i < n; i++)
	{
		p[i] = (seed + i * 5) % 13;
	}
}

static unsigned checksum(const float* f, int n, const int* a, int na, const int* b, int nb, int extra)
{
	unsigned h = (unsigned)extra;

	for(int i = 0; i < n; i++)
	{
		h = h * 131u + (unsigned)(int)f[i];
	}
	for(int i = 0; i < na; i++)
	{
		h = h * 131u + (unsigned)a[i];
	}
	for(int i = 0; i < nb; i++)
	{
		h = h * 131u + (unsigned)b[i];
	}

	return h;
}

int main()
{
	static float a[max_val], b[max_val], c[max_val];
	static int ia[max_val], ib[max_val], ic[max_val], mypred[max_val], out[max_val * 2];
	int sizes[5] = {7, 16, 1023, 1024, 2048};

	for(int s = 0; s < 5; s++)
	{
		int n = sizes[s];

		fill_float(a, n, 1);
		fill_float(b, n, 2);
		fill_int(ia, n, 3);
		fill_int(ib, n, 4);
		fill_int(mypred, n, 5);
		f1(n, c, a, b, 3.0f);
		int d = f2(n, ia, ib);
		f3(n, ic, ia, ib, mypred);
		f4(n, out, ia, ib);
		printf("%d %u\n", n, checksum(c, n, ic, n, out, 2 * n, d));
	}

	return 0;
}