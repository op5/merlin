#include <sodium.h>

int main(void)
{
    unsigned char key[crypto_secretbox_KEYBYTES];
    FILE * f;
    size_t written;

    if (sodium_init() < 0) {
        printf("%s\n", "Could init crypo lib. Exiting.");
        exit(1);
    }

    crypto_secretbox_keygen(key);

    f = fopen("/opt/monitor/op5/merlin/key", "w");

    if (f == NULL) {
        printf("%s\n", "Failed to open file file for writing");
        exit(1);
    }

    written = fwrite(key, crypto_secretbox_KEYBYTES, 1, f);
    if (written != 1) {
        printf("%s\n", "Failed writing to file");
        printf("Written: %ld\n", written);
        exit(1);
    }
    if (fclose(f) != 0) {
        printf("%s\n", "Failed to close file stream");
        exit(1);
    }
    return 0;
}
