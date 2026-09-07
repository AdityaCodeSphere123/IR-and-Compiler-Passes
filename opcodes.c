#include <stdio.h>
#include <stdlib.h>


typedef
struct myStruct
{
	int scalar;
	int array[2][2];
	int* ptr;
} myStruct;

volatile int runtimeindex = 1;

void __attribute__((noinline)) f1(void)
{
	const int compiletimeindex = 0;

	myStruct arr[2];

	arr[runtimeindex].scalar = 1;
	arr[runtimeindex].array[compiletimeindex][compiletimeindex] = 2;
	arr[runtimeindex].ptr = (int*)arr;
}

int loopcarried = 0;

void __attribute__((noinline)) f2(void)
{
	for(int i = 0; i < 3; i++)
	{
		loopcarried += 1;
		float myf = loopcarried/2.0f;

		if(loopcarried == 4) break;
		else if(myf == 2.0) break;
	}
}


void __attribute__((noinline)) f3(void)
{
	int a = 1;
	switch(a)
	{
		case 0:
			f1();
			break;

		case 1: {
			int t = (runtimeindex > 1) ? loopcarried : 7;	 
			loopcarried += t;
			f1();
			break;
		}

		case 2: {
			long long a = loopcarried;	 
			int b = (int)a;			 
			loopcarried = b;
			break;
		}

		case 3: {
			float d = (float)loopcarried;	 
			loopcarried = (int)(d * 1.5f);	 
			break;
		}
	}
}



int main()
{

}