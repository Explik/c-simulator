#include <stdio.h>

int func2(int n) {
  return n;
}

int func1(int n) {
  int i = func2(n);
  return n * i + n * i * 2;
}

int main(void) {
  int n = 5;
  printf("Factorial of %d: %d\n" , n , func1(n));
  printf("Factorial of %d: %d\n" , n , func1(n));
  return 0;
}