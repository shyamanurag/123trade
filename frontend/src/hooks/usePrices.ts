import { useEffect, useState } from 'react';
import useSocket from './useSocket';

export interface PricePoint {
  timestamp: number;
  price: number;
  symbol: string;
}

export default function usePrices(symbol: string) {
  const [points, setPoints] = useState<PricePoint[]>([]);

  useSocket((msg) => {
    if (msg.symbol === symbol && typeof msg.price === 'number') {
      setPoints((prev) => [...prev.slice(-99), { timestamp: Date.now(), price: msg.price, symbol }]);
    }
  });

  // initial empty array
  useEffect(() => {
    setPoints([]);
  }, [symbol]);

  return points;
}
