/**
 * ProjectsByStatusChart — renders a pie chart with status distribution data
 * and an empty state when no data is available.
 */

import { render, screen } from "@testing-library/react";
import { ProjectsByStatusChart } from "@/features/dashboard/charts/ProjectsByStatusChart";

// Recharts relies on SVG and ResizeObserver — mock the module so chart
// components render simple, testable DOM in jsdom.
jest.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  PieChart: ({ children, ...props }: { children: React.ReactNode; [key: string]: unknown }) => (
    <div data-testid="pie-chart" aria-label={props["aria-label"] as string}>
      {children}
    </div>
  ),
  Pie: ({
    children,
    data,
  }: {
    children: React.ReactNode;
    data: Array<{ status: string; count: number }>;
  }) => (
    <div data-testid="pie">
      {data?.map((d) => (
        <span key={d.status} data-value={d.count}>
          {d.status}
        </span>
      ))}
      {children}
    </div>
  ),
  Cell: () => <div data-testid="cell" />,
  Tooltip: () => <div data-testid="tooltip" />,
  Legend: () => <div data-testid="legend" />,
}));

describe("ProjectsByStatusChart", () => {
  it("renders the pie chart with data", () => {
    const data = [
      { status: "aprobado", count: 20 },
      { status: "en_ejecucion", count: 10 },
    ];

    render(<ProjectsByStatusChart data={data} />);

    expect(screen.getByTestId("pie-chart")).toBeInTheDocument();
    expect(screen.getByTestId("pie")).toBeInTheDocument();
    expect(screen.getByText("aprobado")).toBeInTheDocument();
    expect(screen.getByText("en_ejecucion")).toBeInTheDocument();
  });

  it("renders empty state when data is empty", () => {
    render(<ProjectsByStatusChart data={[]} />);

    expect(screen.getByText("No hay datos de proyectos por estado")).toBeInTheDocument();
    expect(screen.queryByTestId("pie-chart")).not.toBeInTheDocument();
  });
});
