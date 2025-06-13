import { useQuery } from '@tanstack/react-query';
import api from './useApi';

export default function useOrders() {
  return useQuery(['orders'], async () => {
    const { data } = await api.get('/orders');
    return data;
  }, {
    refetchInterval: 5000,
  });
}
