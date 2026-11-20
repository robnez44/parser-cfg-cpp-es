// ERROR: semantic 7
void ejecutar() {
    cout << "ejecutar" << endl;
}

int main() {
    if (ejecutar())
        return 1;
    return 0;
}
