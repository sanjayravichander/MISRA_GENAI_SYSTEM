#include <stdio.h>
#include <stdint.h>
#include "calc.h"

static int validate_input(int value)
{
    if (value < 0)
    {
        return 0;
    }

    if ((uint8_t)value > 200U)
    {
        return 0;
    }

    return 1;
}

int main(void)
{
    int x = 10;
    int y = 20;
    uint16_t small;

    int total = calculate_total(x, y);

    small = total + 300;

    printf("%d\n", total);

    if (validate_input(total) == 1)
    {
        total = total * total;
    }

    return 0;
}