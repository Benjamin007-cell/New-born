use std::io::Write;
use std::process::{Command,Stdio};
fn replay(input:&str)->std::process::Output {
 let mut child=Command::new(env!("CARGO_BIN_EXE_replay-engine")).stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::piped()).spawn().unwrap();
 child.stdin.take().unwrap().write_all(input.as_bytes()).unwrap(); child.wait_with_output().unwrap()
}
#[test] fn demo_outputs_three_fills(){
 let out=replay(include_str!("../data/events.csv"));
 assert!(out.status.success());
 let s=String::from_utf8(out.stdout).unwrap();
 assert_eq!(s.lines().count(),4);
 assert!(s.contains("3,ask1,buy1,10000,200"));
 assert!(s.contains("3,ask2,buy1,10000,50"));
 assert!(s.contains("6,bid1,sell1,9995,100"));
}
#[test] fn rejects_unsorted_input(){
 let out=replay("2,add,a,buy,100,1\n1,add,b,buy,100,1\n");
 assert!(!out.status.success());
 assert!(String::from_utf8(out.stderr).unwrap().contains("nondecreasing"));
}
#[test] fn rejects_unknown_cancel(){assert!(!replay("1,cancel,missing,,,\n").status.success());}
