void notify(char *metadata, void *data);
int main()
{
  int temp0;
  int temp1;
  int temp2;
  int temp3;
  int temp4;
  int temp5;
  int temp6;
  int temp7;
  int temp8;
  int temp9;
  int i = (temp0 = 5, notify("t=int;l=[2,12,2,13]", &temp0), temp0);
  int j = (temp1 = i, notify("t=int;l=[3,12,3,13]", &temp1), temp2 = temp1 + 1, notify("t=int;l=[3,12,3,17]", &temp2), temp3 = temp2 < 5, notify("t=int;l=[3,12,3,21]", &temp3), temp4 = i, notify("t=int;l=[3,25,3,26]", &temp4), temp5 = temp4 > 6, notify("t=int;l=[3,25,3,30]", &temp5), temp6 = temp3 && temp5, notify("t=int;l=[3,12,3,30]", &temp6), temp6);
  return temp7 = i, notify("t=int;l=[4,11,4,12]", &temp7), temp8 = j, notify("t=int;l=[4,15,4,16]", &temp8), temp9 = temp7 + temp8, notify("t=int;l=[4,11,4,16]", &temp9), temp9;
}

