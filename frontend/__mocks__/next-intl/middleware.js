// Mock for next-intl/middleware
const createMockMiddleware = () => {
  return (request) => {
    // Return a simple NextResponse-like object
    const { NextResponse } = require('next/server');
    return NextResponse.next();
  };
};

module.exports = createMockMiddleware;
module.exports.default = createMockMiddleware;
