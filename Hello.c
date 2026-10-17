#include <stdio.h>

void check_sid(unsigned char data[]) {
     if (data[1] == 0x27) {
        printf("Security Access \n");

    } else if (data[1] == 0x10) {
        printf("Session Control \n");
    
    } else {
        printf("Wrong SID \n");
    }
}

int main() {
    unsigned char seed_byte = 170; // Example seed byte (0xAA)
    printf("Seed byte: %d\n", seed_byte);
    unsigned char data[8];  // Array of 8 unsigned char same shape as your []
    data[0] = 0x02;
    data[1] = 0x27;
    data[2] = 0x02;
    
    check_sid(data);

    return 0;
}
