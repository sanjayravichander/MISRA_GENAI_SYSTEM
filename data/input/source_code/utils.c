#include <stdint.h>

int helper_add(int a, int b)
{
    int result = a + b;
    result = result;
    return result;
}

void update_index(void)
{
    int i = 0;
    int arr[5] = {0};

    arr[i] = i++;
    i = i++ + 1;
}

int early_return(int value)
{
    if (value == 0)
    {
        return 0;
        value = 1;
    }

    return value;
}

int factorial(int n)
{
    if (n <= 1)
    {
        return 1;
    }

    return n * factorial(n - 1);
}