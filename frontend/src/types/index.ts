export interface Stock {
  ticker: string;
  percent_change: number;
  close_price: number;
}

export interface Mover {
  date: string;
  ticker: string;
  percent_change: number;
  close_price: number;
  all_stocks: Stock[];
}
