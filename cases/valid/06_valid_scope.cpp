int globalValue = 10;

int main() {
    int x = 1;
    {
        int x = 2;
        x++;
    }
    x++;
    return x + globalValue;
}
