use std::{env,io::{self,BufRead}};
use replay_engine::{Book,Config,Order,Side};
fn run()->Result<(),String>{
 let args:Vec<String>=env::args().collect();
 let mut config=Config::default();
 let mut i=1;
 while i<args.len(){
  let value=args.get(i+1).ok_or("missing option value")?;
  match args[i].as_str(){
   "--maker-bps"=>config.maker_bps=value.parse().map_err(|_|"invalid maker bps")?,
   "--taker-bps"=>config.taker_bps=value.parse().map_err(|_|"invalid taker bps")?,
   "--multiplier"=>config.notional_multiplier=value.parse().map_err(|_|"invalid multiplier")?,
   "--ticks"=>config.ticks=value.split(',').map(|s|{let (a,b)=s.split_once(':').ok_or("expected lower:tick")?;Ok((a.parse().map_err(|_|"bad lower")?,b.parse().map_err(|_|"bad tick")?))}).collect::<Result<Vec<_>,String>>()?,
   _=>return Err(format!("unknown option {}",args[i])),
  } i+=2;
 }
 let mut book=Book::new(config)?; let mut last=None;
 println!("timestamp,maker,taker,price,quantity,maker_fee,taker_fee");
 for (line_no,line) in io::stdin().lock().lines().enumerate(){
  let line=line.map_err(|e|e.to_string())?;
  if line.trim().is_empty() || line.starts_with('#') || line=="timestamp,action,id,side,price,quantity" {continue;}
  let result=(||->Result<(),String>{
   let c:Vec<_>=line.split(',').collect(); if c.len()!=6 {return Err("expected six CSV fields".into());}
   let ts:u64=c[0].parse().map_err(|_|"invalid timestamp")?;
   if last.map_or(false,|p|ts<p){return Err("timestamps must be nondecreasing".into());}
   last=Some(ts);
   if c[2].is_empty() || !c[2].chars().all(|v|v.is_ascii_alphanumeric() || "_-".contains(v)){return Err("id must use letters, digits, underscore or hyphen".into());}
   match c[1] {
    "cancel"=>book.cancel(c[2])?,
    "add"=>{
     let side=match c[3]{"buy"=>Side::Buy,"sell"=>Side::Sell,_=>return Err("invalid side".into())};
     let order=Order{id:c[2].into(),side,price:c[4].parse().map_err(|_|"invalid price")?,qty:c[5].parse().map_err(|_|"invalid quantity")?};
     for f in book.submit(order)? {println!("{},{},{},{},{},{:.8},{:.8}",ts,f.maker,f.taker,f.price,f.qty,f.maker_fee,f.taker_fee);}
    },_=>return Err("action must be add or cancel".into())
   } Ok(())
  })(); result.map_err(|e|format!("line {}: {}",line_no+1,e))?;
 } Ok(())
}
fn main(){if let Err(e)=run(){eprintln!("{e}");std::process::exit(1);}}
