OPENQASM 3.0;
include "stdgates.inc";
bit[3] data;
bit[2] syndrome;
qubit[3] q0;
qubit[2] q1;
x q0[0];
barrier q0[0], q0[1], q0[2];
cx q0[0], q0[1];
cx q0[0], q0[2];
barrier q0[0], q0[1], q0[2];
cx q0[0], q1[0];
cx q0[1], q1[0];
cx q0[0], q1[1];
cx q0[2], q1[1];
barrier q0[0], q0[1], q0[2], q1[0], q1[1];
syndrome[0] = measure q1[0];
syndrome[1] = measure q1[1];
if (syndrome[0]) {
  x q1[0];
}
if (syndrome[1]) {
  x q1[1];
}
barrier q0[0], q0[1], q0[2], q1[0], q1[1];
if (syndrome == 3) {
  x q0[0];
}
if (syndrome == 1) {
  x q0[1];
}
if (syndrome == 2) {
  x q0[2];
}
barrier q0[0], q0[1], q0[2];
barrier q0[0], q0[1], q0[2];
data[0] = measure q0[0];
data[1] = measure q0[1];
data[2] = measure q0[2];
