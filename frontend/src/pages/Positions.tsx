import usePositions from '../hooks/usePositions';

export default function Positions() {
  const { data: positions, isLoading } = usePositions();
  if (isLoading) return <p>Loading…</p>;
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full bg-white">
        <thead>
          <tr>
            <th className="px-4 py-2">Symbol</th>
            <th className="px-4 py-2">Qty</th>
            <th className="px-4 py-2">Avg Price</th>
            <th className="px-4 py-2">PnL</th>
          </tr>
        </thead>
        <tbody>
          {positions?.map((p: any) => (
            <tr key={p.symbol} className="text-center border-t">
              <td className="px-4 py-2">{p.symbol}</td>
              <td className="px-4 py-2">{p.quantity}</td>
              <td className="px-4 py-2">{p.avg_price}</td>
              <td className="px-4 py-2">{p.pnl}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
