1  #include <stdio.h>
       2  #include <string.h>
       3  
       4  static char log_buffer[64];
       5  
       6  void log_message(char * msg)
       7  {
       8      int status = 0;
       9  
      10      strcpy(log_buffer, msg);
      11  
      12      status = puts(log_buffer);
      13  
      14      printf("puts returned: %d\n", status);
      15  }