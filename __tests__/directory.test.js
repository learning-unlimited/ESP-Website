// 
const $ = require("jquery");

global.$ = $;
global.$j = $;
global.jQuery = $;

global.has_autoscheduler_frontend = "False";
// global.Cell = function(el, section, a, b, matrix) {
//     this.el = el;
// };
// MOCK CELL
global.Cell = function(el) {
  this.el = el;
};

const { Directory } = require(
  "../esp/public/media/scripts/ajaxschedulingmodule/ESP/Directory.js"
);

test("Directory constructor exists", () => {
  expect(typeof Directory).toBe("function");
});

describe("Directory render()", () => {
  
  let mockSections;
  let container;

  beforeEach(() => {
    document.body.innerHTML = `<div id="container"></div>`;
    container = $j("#container");

    mockSections = {
      filtered_sections: jest.fn(() => [
        {
          id: 1,
          title: "Math 101",
          parent_class: 10
        }
      ]),
      getBaseUrlString: jest.fn(() => "/base/")
    };
  });

  test("renders table with one row", () => {
    const directory = new Directory(
      mockSections,
      container,
      null,
      {}
    );

    directory.render();

    const table = container.find("table");
    expect(table.length).toBe(1);

    const rows = table.find("tr");
    expect(rows.length).toBe(1);
  });

  test("renders correct section title and links", () => {
    const directory = new Directory(
      mockSections,
      container,
      null,
      {}
    );

    directory.render();

    const rowHTML = container.find("tr").html();

    expect(rowHTML).toContain("Math 101");
    expect(rowHTML).toContain("/base/manageclass/10");
    expect(rowHTML).toContain("/base/editclass/10");
    expect(rowHTML).toContain("/base/classavailability/10");
  });

  test("renders multiple rows when multiple sections exist", () => {

    mockSections.filtered_sections.mockReturnValue([
      { id: 1, title: "Math 101", parent_class: 10 },
      { id: 2, title: "Physics 201", parent_class: 20 }
    ]);

    const directory = new Directory(
      mockSections,
      container,
      null,
      {}
    );

    directory.render();

    const rows = container.find("tr");

    expect(rows.length).toBe(2);
    expect(container.html()).toContain("Physics 201");
  });
  test("does NOT render Optimize link when autoscheduler disabled", () => {

  global.has_autoscheduler_frontend = "False";

  const directory = new Directory(
    mockSections,
    container,
    null,
    {}
  );

  directory.render();

  expect(container.html()).not.toContain("Optimize");
});
test("renders Optimize link when autoscheduler enabled", () => {

  global.has_autoscheduler_frontend = "True";

  const directory = new Directory(
    mockSections,
    container,
    null,
    {}
  );

  directory.render();

  expect(container.html()).toContain("Optimize");
  expect(container.html()).toContain("autoscheduler?section=1");
});
test("renders empty table when no sections exist", () => {

  mockSections.filtered_sections.mockReturnValue([]);

  const directory = new Directory(
    mockSections,
    container,
    null,
    {}
  );

  directory.render();

  const table = container.find("table");
  expect(table.length).toBe(1);

  const rows = container.find("tr");
  expect(rows.length).toBe(0);
});
test("calls filtered_sections and getBaseUrlString during render", () => {

  const directory = new Directory(
    mockSections,
    container,
    null,
    {}
  );

  directory.render();

  expect(mockSections.filtered_sections).toHaveBeenCalled();
  expect(mockSections.getBaseUrlString).toHaveBeenCalled();
});
test("clears container before re-rendering", () => {
  const directory = new Directory(mockSections, container, null, {});

  directory.render();
  const firstTable = container.find("table");

  directory.render();
  const secondTable = container.find("table");

  expect(container.find("table").length).toBe(1);
  expect(secondTable[0]).not.toBe(firstTable[0]);
});
test("each row contains section title cell", () => {
  const directory = new Directory(mockSections, container, null, {});
  directory.render();

  const firstRow = container.find("tr").first();
  expect(firstRow.find("td").first().text()).toContain("Math 101");
});
test("Optimize link appears only when autoscheduler enabled", () => {
  global.has_autoscheduler_frontend = "False";
  const directory = new Directory(mockSections, container, null, {});
  directory.render();
  expect(container.html()).not.toContain("Optimize");

  global.has_autoscheduler_frontend = "True";
  directory.render();
  expect(container.html()).toContain("Optimize");
});
test("renders multiple sections in correct order", () => {
  mockSections.filtered_sections.mockReturnValue([
    { id: 1, title: "Math 101", parent_class: 10 },
    { id: 2, title: "Physics 201", parent_class: 20 },
    { id: 3, title: "Chemistry 301", parent_class: 30 }
  ]);

  const directory = new Directory(mockSections, container, null, {});
  directory.render();

  const rows = container.find("tr");
  expect(rows.length).toBe(3);
  expect(rows.eq(0).text()).toContain("Math 101");
  expect(rows.eq(1).text()).toContain("Physics 201");
  expect(rows.eq(2).text()).toContain("Chemistry 301");
});
test("re-renders when schedule-changed event is triggered", () => {
  const directory = new Directory(mockSections, container, null, {});

  // Initial render
  directory.render();
  expect(container.html()).toContain("Math 101");

  // Change mock data
  mockSections.filtered_sections.mockReturnValue([
    { id: 2, title: "Physics 201", parent_class: 20 }
  ]);

  // Trigger the event
  $j("body").trigger("schedule-changed");

  // After event, it should re-render with new data
  expect(container.html()).toContain("Physics 201");
  expect(container.html()).not.toContain("Math 101");
});
test("handles undefined filtered_sections safely", () => {
  mockSections.filtered_sections.mockReturnValue(undefined);

  const directory = new Directory(mockSections, container, null, {});

  expect(() => directory.render()).not.toThrow();
});
});
