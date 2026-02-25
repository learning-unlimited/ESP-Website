const $ = require("jquery");
global.$ = $;
global.$j = $;
global.jQuery = $;

// MOCK Cell must be global before requiring TableRow
global.Cell = function(el) {
  this.el = el || $j("<td class='selectable-cell'/>");
};

// Now require TableRow
const { TableRow } = require("../esp/public/media/scripts/ajaxschedulingmodule/ESP/Directory.js");

describe("TableRow", () => {
  let mockSection, mockEl, mockDirectory;

  beforeEach(() => {
    document.body.innerHTML = `<table><tbody></tbody></table>`;
    mockEl = $j("<tr/>");

    mockSection = { id: 1, title: "Math 101", parent_class: 10 };
    mockDirectory = {
      matrix: {},
      sections: { getBaseUrlString: jest.fn(() => "/base/") }
    };
    global.has_autoscheduler_frontend = "True";
  });

  test("constructor exists", () => {
    const row = new TableRow(mockSection, mockEl, mockDirectory);
    expect(row).toBeDefined();
    expect(row.section).toBe(mockSection);
  });

  test("render() creates correct HTML for links and title", () => {
    const row = new TableRow(mockSection, mockEl, mockDirectory);
    row.render();
    const html = row.el.html();
    expect(html).toContain("Math 101");
    expect(html).toContain("/base/manageclass/10");
  });

  test("renders Optimize link when enabled", () => {
    global.has_autoscheduler_frontend = "True";
    const row = new TableRow(mockSection, mockEl, mockDirectory);
    row.render();
    expect(row.el.html()).toContain("Optimize");
  });

  test("does NOT render Optimize link when disabled", () => {
    global.has_autoscheduler_frontend = "False";
    const row = new TableRow(mockSection, mockEl, mockDirectory);
    row.render();
    expect(row.el.html()).not.toContain("Optimize");
  });
});