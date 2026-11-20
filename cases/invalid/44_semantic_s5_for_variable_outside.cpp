// ERROR: semantic 6
int main() {
    for (int i = 0; i < 3; i++) {
        i++;
    }
    i++;
    return 0;
}
