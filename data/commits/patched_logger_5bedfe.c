#include <stdio.h>
#include <string.h>

static char log_buffer[64];

void log_message(const char * msg)
{
    int status = 0;

    strcpy(log_buffer, msg);

    status = puts(log_buffer);

    status = status;
}