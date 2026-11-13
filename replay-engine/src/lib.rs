use std::collections::{BTreeMap, HashSet, VecDeque};
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Side { Buy, Sell }
#[derive(Clone, Debug)]
pub struct Order { pub id: String, pub side: Side, pub price: u64, pub qty: u64 }
#[derive(Clone, Debug, PartialEq)]
pub struct Fill { pub maker: String, pub taker: String, pub price: u64, pub qty: u64, pub maker_fee: f64, pub taker_fee: f64 }
#[derive(Clone, Debug)]
pub struct Config {
    /// Sorted (inclusive lower bound, tick) pairs. Prices are integer minor units.
    pub ticks: Vec<(u64,u64)>,
    pub maker_bps: f64, pub taker_bps: f64,
    /// Equity: 1. Bonds quoted per 100 face: 0.01. Fees use this multiplier.
    pub notional_multiplier: f64,
}
impl Default for Config { fn default() -> Self { Self { ticks: vec![(0,1)], maker_bps: 0.0, taker_bps: 0.0, notional_multiplier: 1.0 } } }
pub struct Book {
    bids: BTreeMap<u64,VecDeque<Order>>, asks: BTreeMap<u64,VecDeque<Order>>,
    seen: HashSet<String>, config: Config,
}
impl Book {
    pub fn new(config: Config) -> Result<Self,String> {
        if config.ticks.is_empty() || config.ticks[0].0 != 0 || config.ticks.iter().any(|x| x.1==0)
            || config.ticks.windows(2).any(|w| w[0].0>=w[1].0)
            || !config.maker_bps.is_finite() || !config.taker_bps.is_finite()
            || !config.notional_multiplier.is_finite() || config.notional_multiplier<=0.0 { return Err("invalid config".into()); }
        Ok(Self { bids:BTreeMap::new(), asks:BTreeMap::new(), seen:HashSet::new(), config })
    }
    pub fn submit(&mut self, mut order:Order)->Result<Vec<Fill>,String> {
        let tick=self.config.ticks.iter().rev().find(|(lower,_)| order.price>=*lower).unwrap().1;
        if order.id.is_empty() || self.seen.contains(&order.id) || order.qty==0 || order.price==0 || order.price%tick!=0 {
            return Err("duplicate id, empty id, nonpositive quantity/price, or off-tick price".into());
        }
        self.seen.insert(order.id.clone());
        let opposite=if order.side==Side::Buy { &mut self.asks } else { &mut self.bids };
        let mut fills=Vec::new();
        while order.qty>0 {
            let best=if order.side==Side::Buy { opposite.keys().next().copied() } else { opposite.keys().next_back().copied() };
            let price=match best { Some(p)=>p, None=>break };
            if (order.side==Side::Buy && price>order.price) || (order.side==Side::Sell && price<order.price) { break; }
            let level=opposite.get_mut(&price).unwrap();
            let maker=level.front_mut().unwrap();
            let qty=order.qty.min(maker.qty);
            let notional=price as f64*qty as f64*self.config.notional_multiplier;
            fills.push(Fill { maker:maker.id.clone(), taker:order.id.clone(), price, qty,
                maker_fee:notional*self.config.maker_bps/10000.0, taker_fee:notional*self.config.taker_bps/10000.0 });
            order.qty-=qty; maker.qty-=qty;
            if maker.qty==0 {level.pop_front();}
            if level.is_empty() {opposite.remove(&price);}
        }
        if order.qty>0 {
            let own=if order.side==Side::Buy {&mut self.bids} else {&mut self.asks};
            own.entry(order.price).or_default().push_back(order);
        }
        Ok(fills)
    }
    pub fn cancel(&mut self,id:&str)->Result<(),String> {
        for levels in [&mut self.bids,&mut self.asks] {
            let found=levels.iter().find_map(|(p,q)|q.iter().position(|o|o.id==id).map(|i|(*p,i)));
            if let Some((price,index))=found {
                let queue=levels.get_mut(&price).unwrap(); queue.remove(index);
                if queue.is_empty(){levels.remove(&price);} return Ok(());
            }
        }
        Err(format!("unknown active order: {id}"))
    }
    pub fn depth(&self)->(Vec<(u64,u64)>,Vec<(u64,u64)>) {
        (self.bids.iter().rev().map(|(p,q)|(*p,q.iter().map(|o|o.qty as u128).sum::<u128>().min(u64::MAX as u128) as u64)).collect(),
         self.asks.iter().map(|(p,q)|(*p,q.iter().map(|o|o.qty as u128).sum::<u128>().min(u64::MAX as u128) as u64)).collect())
    }
}
#[cfg(test)] mod tests {
 use super::*;
 fn o(id:&str,side:Side,price:u64,qty:u64)->Order {Order{id:id.into(),side,price,qty}}
 #[test] fn price_time_and_partial() {
  let mut b=Book::new(Config::default()).unwrap();
  b.submit(o("a",Side::Sell,101,5)).unwrap(); b.submit(o("b",Side::Sell,100,2)).unwrap(); b.submit(o("c",Side::Sell,100,4)).unwrap();
  let f=b.submit(o("x",Side::Buy,101,5)).unwrap();
  assert_eq!(f.iter().map(|f|(f.maker.as_str(),f.qty,f.price)).collect::<Vec<_>>(),vec![("b",2,100),("c",3,100)]);
  assert_eq!(b.depth().1,vec![(100,1),(101,5)]);
 }
 #[test] fn ticks_fees_cancel_and_duplicate() {
  let mut b=Book::new(Config{ticks:vec![(0,1),(100,5)],maker_bps:-1.0,taker_bps:2.0,notional_multiplier:0.01}).unwrap();
  assert!(b.submit(o("bad",Side::Buy,101,1)).is_err());
  b.submit(o("a",Side::Buy,100,10)).unwrap();
  let f=b.submit(o("b",Side::Sell,100,4)).unwrap();
  assert!((f[0].taker_fee-0.0008).abs()<1e-10); assert!(f[0].maker_fee<0.0);
  b.cancel("a").unwrap(); assert!(b.cancel("a").is_err());
  assert!(b.submit(o("a",Side::Buy,100,1)).is_err()); assert!(b.depth().0.is_empty());
 }
 #[test] fn sell_sweeps_best_bid() {
  let mut b=Book::new(Config::default()).unwrap();
  b.submit(o("a",Side::Buy,99,2)).unwrap(); b.submit(o("b",Side::Buy,100,2)).unwrap();
  let f=b.submit(o("s",Side::Sell,99,5)).unwrap(); assert_eq!(f[0].maker,"b"); assert_eq!(f[1].maker,"a"); assert_eq!(b.depth().1,vec![(99,1)]);
 }
}
