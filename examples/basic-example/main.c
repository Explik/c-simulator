#include <stdlib.h>
#include <stdio.h>

int main(void){
    int n = 7;
    int step = 1; 
    
    for(int i = 0; 0 <= i && i <= n; i += step){
        for(int j = 0; j <= i; j += 1){
            printf(" %d", j);
        }
        printf("\n");
        
        if(i == n) 
            step = 0-1;
    }
    
    return EXIT_SUCCESS;
}