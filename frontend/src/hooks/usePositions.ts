import { useQuery } from '@tanstack/react-query';
import api from './useApi';

export default function usePositions() {
  return useQuery(['positions'], async () => {
    const { data } = await api.get('/positions');
    return data;
  }, {
    refetchInterval: 5000,
  });
}
