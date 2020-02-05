#include <sodium.h>

int main(void)
{
    unsigned char key[crypto_secretbox_KEYBYTES];
    FILE * f;
    if (sodium_init() < 0) {
        printf("%s\n", "Could init crypo lib. Exiting.");
        exit(1);
    }

    crypto_secretbox_keygen(key);

    f = fopen("/opt/monitor/op5/merlin/key", "w");
    fprintf(f, "%s", key);
    fclose(f);
}
