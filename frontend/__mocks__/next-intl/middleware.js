// Mock for next-intl/middleware
import { NextResponse } from 'next/server';

const createMockMiddleware = () => {
  return (_request) => {
    // Return a simple NextResponse-like object
    return NextResponse.next();
  };
};

export default createMockMiddleware;
export { createMockMiddleware };
