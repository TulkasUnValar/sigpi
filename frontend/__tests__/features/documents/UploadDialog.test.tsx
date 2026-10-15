import { render, screen } from '@testing-library/react';
import { UploadDialog } from './UploadDialog';

describe('UploadDialog', () => {
  it('renders without crashing', () => {
    render(<UploadDialog>Open Dialog</UploadDialog>);
    expect(screen.getByText('Open Dialog')).toBeInTheDocument();
  });
});
