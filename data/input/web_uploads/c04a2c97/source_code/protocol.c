#include <stdint.h>

void parse_frame(uint8_t * data, uint8_t len)
{
    uint8_t i;

    for (i = 0U; i < len; i++)
    {
        data[i] = (uint8_t)(data[i] + 1U);
    }
}

uint8_t make_mask(uint8_t shift)
{
    return (uint8_t)(1U << shift);
}