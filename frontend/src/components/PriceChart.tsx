import { LineChart, Line, XAxis, YAxis, Tooltip } from 'recharts';
import usePrices from '../hooks/usePrices';

interface Props {
  symbol: string;
}

export default function PriceChart({ symbol }: Props) {
  const points = usePrices(symbol);
  return (
    <LineChart width={600} height={300} data={points}>
      <XAxis dataKey="timestamp" tick={false} />
      <YAxis domain={['auto', 'auto']} />
      <Tooltip />
      <Line type="monotone" dataKey="price" stroke="#4f46e5" dot={false} />
    </LineChart>
  );
}
