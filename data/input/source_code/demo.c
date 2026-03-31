#include <stdint.h>
 
#define REG_BASE 0x40000000
 
int device_state;
 
void writeDevice(int value)
{
    uint32_t *ptr = (uint32_t*)REG_BASE;
 
    if(value > 100)
        device_state = 1;
    else
        device_state = 0;
 
    *(ptr + device_state) = value;   /* pointer arithmetic */
}
 
int readDevice()
{
    uint32_t *ptr = (uint32_t*)REG_BASE;
    return *(ptr + device_state);
}
 
void process()
{
    int i;
 
    for(i = 0; i < 20; i++)
    {
        writeDevice(i * 5);
    }
 
    int data = readDevice();
 
    if(data = 50)   /* MISRA violation */
    {
        writeDevice(data);
    }
}