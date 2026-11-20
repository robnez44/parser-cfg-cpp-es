int main() {
    int sum = 0;
    for (int i = 1; i <= 5; i++) {
        if (i % 2 == 0)
            continue;
        sum += i;
    }

    int i = 0;
    while (i < 3) {
        i++;
        if (i == 2)
            break;
    }

    do {
        i--;
    } while (i > 0);

    switch (i) {
        case 0:
            sum++;
            break;
        default:
            sum--;
    }
    return sum;
}
