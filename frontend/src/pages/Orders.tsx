import useOrders from '../hooks/useOrders';

export default function Orders() {
  const { data: orders, isLoading } = useOrders();
  if (isLoading) return <p>Loading…</p>;
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full bg-white">
        <thead>
          <tr>
            <th className="px-4 py-2">ID</th>
            <th className="px-4 py-2">Symbol</th>
            <th className="px-4 py-2">Side</th>
            <th className="px-4 py-2">Qty</th>
            <th className="px-4 py-2">Status</th>
          </tr>
        </thead>
        <tbody>
          {orders?.map((o: any) => (
            <tr key={o.id} className="text-center border-t">
              <td className="px-4 py-2">{o.id}</td>
              <td className="px-4 py-2">{o.symbol}</td>
              <td className="px-4 py-2">{o.side}</td>
              <td className="px-4 py-2">{o.quantity}</td>
              <td className="px-4 py-2">{o.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
