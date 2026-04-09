#include <stdio.h>

void func(void)
{
    int x = 0;       /* initialize x */
    int y;

    y = x + 1;   /* x read before set */

    printf("%d\n", y);
}