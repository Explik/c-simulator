double get_constant(int i, int i2);

int main() {
    double i = 5;
    double j = get_constant(-i * 5, 6);
    return 5 * i++;
}

double get_constant(int i, int i2) {
    return 5;
}