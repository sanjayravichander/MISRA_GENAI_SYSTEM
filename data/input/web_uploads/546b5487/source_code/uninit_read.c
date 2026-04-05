#include <stdio.h>

void func(void)
{
    int x;       /* no init */
    int y;

    y = x + 1;   /* x read before set */

    printf("%d\n", y);
}