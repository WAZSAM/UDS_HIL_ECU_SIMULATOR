#include <stdio.h>

// Identifies a UDS service from the service ID in the data array.
void check_sid(unsigned char data[]) {
     // 0x27 is the UDS SecurityAccess service.
     if (data[1] == 0x27) {
        printf("Security Access \n");

    // 0x10 is the UDS DiagnosticSessionControl service.
    } else if (data[1] == 0x10) {
        printf("Session Control \n");
    
    } else {
        // Any other service ID is not recognized by this example.
        printf("Wrong SID \n");
    }
}

int main() {
    // Example seed value; this program only prints it and does not use it
    // to perform a SecurityAccess exchange.
    unsigned char seed_byte = 170; // Example seed byte (0xAA)
    printf("Seed byte: %d\n", seed_byte);

    // Create a sample UDS payload: length byte, service ID, and sub-function.
    unsigned char data[8] = {0};
    data[0] = 0x02;
    data[1] = 0x27;
    data[2] = 0x02;
    
    // Print which service the sample payload represents.
    check_sid(data);

    // Return success to the operating system.
    return 0;
}
