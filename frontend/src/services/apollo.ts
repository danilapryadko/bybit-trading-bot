import { ApolloClient, InMemoryCache, createHttpLink } from '@apollo/client';

const API_URL = import.meta.env.VITE_API_URL || 'https://bybit-danila-api.fly.dev';

const httpLink = createHttpLink({
  uri: `${API_URL}/graphql/`,
  credentials: 'same-origin',
});

export const apolloClient = new ApolloClient({
  link: httpLink,
  cache: new InMemoryCache(),
  defaultOptions: {
    watchQuery: {
      fetchPolicy: 'network-only',
    },
    query: {
      fetchPolicy: 'network-only',
    },
  },
});

export default apolloClient;