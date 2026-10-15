import { render, screen, fireEvent } from '@testing-library/react';
import { DocumentsFilters } from './DocumentsFilters';

describe('DocumentsFilters', () => {
  const mockOnChange = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders filter inputs', () => {
    render(<DocumentsFilters filters={{}} onChange={mockOnChange} />);

    expect(screen.getByLabelText(/buscar/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/tipo/i)).toBeInTheDocument();
  });

  it('calls onChange when search input changes', () => {
    render(<DocumentsFilters filters={{}} onChange={mockOnChange} />);

    const searchInput = screen.getByLabelText(/buscar/i);
    fireEvent.change(searchInput, { target: { value: 'test' } });

    expect(mockOnChange).toHaveBeenCalledWith({ search: 'test' });
  });

  it('calls onChange when doc_type filter changes', () => {
    render(<DocumentsFilters filters={{}} onChange={mockOnChange} />);

    const typeSelect = screen.getByLabelText(/tipo/i);
    fireEvent.change(typeSelect, { target: { value: 'contract' } });

    expect(mockOnChange).toHaveBeenCalledWith({ doc_type: 'contract' });
  });

  it('displays current filter values', () => {
    const filters = { search: 'test', doc_type: 'contract' };
    render(<DocumentsFilters filters={filters} onChange={mockOnChange} />);

    const searchInput = screen.getByLabelText(/buscar/i) as HTMLInputElement;
    expect(searchInput.value).toBe('test');
  });
});
