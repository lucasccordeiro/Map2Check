int main() {
  int k = __VERIFIER_nondet_int();
  int n = __VERIFIER_nondet_int();  
  
  int x = k;
  int y = k;
  while (x < n) {
    x++;
    y++;
  }
  assert (x >= y);
  assert (x <= y);  
  return 0;
}
