#include "calc.h"

int g_total = 0;

int calculate_total(int a, int b)
{
    int result = a + b;
    g_total = result;
    return result;
}