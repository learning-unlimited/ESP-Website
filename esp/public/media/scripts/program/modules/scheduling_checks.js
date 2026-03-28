var auto_running = false;
var myInterval;
$j(function () {
  function refreshAll() {
    if (auto_running) {
      $j("button.refresh-button").click();
      // Allow for updating fresh interval while the refresh is already running
      myInterval = setTimeout(refreshAll, $j("[name=refresh_interval]").val() * 1000);
    }
  }
  $j("[name=refresh]").click(function () {
    if (auto_running) {
      auto_running = false;
      // Change button class and text
      $j(this).addClass("btn-success");
      $j(this).removeClass("btn-danger");
      $j(this).html("Start Auto Refresh");

      // Stop autorefreshing
      clearTimeout(myInterval);
    } else {
      auto_running = true;
      // Change button class and text
      $j(this).addClass("btn-danger");
      $j(this).removeClass("btn-success");
      $j(this).html("Stop Auto Refresh");

      // Start autorefreshing
      refreshAll();
    }
  });
});

/**
 * List of scheduling checks.
 *
 * Should have individual SchedulingCheck elements as children.
 */
var SchedulingCheckList = React.createClass({
  displayName: "SchedulingCheckList",
  render: function () {
    return /*#__PURE__*/React.createElement("div", {
      className: "scheduling-check-list"
    }, this.props.children);
  }
});

/**
 * A single scheduling check.
 *
 * This might or might not be loaded yet; clicking the heading will load the
 * data from the server and expand it.
 * 
 * There is supposedly a functionality in which clicking on a table row will cause it
 * to be greyed out, however whether this actually happens depends on your
 * scheduling_checks.css (clicking could possibly do nothing, or possibly
 * do other things).
 *
 * Likewise, clicking on a table header will sort by that column. You can also
 * add formatting in scheduling_checks.css so that the selected header will
 * look different, e.g. be colored differently.
 */
var SchedulingCheck = React.createClass({
  displayName: "SchedulingCheck",
  propTypes: {
    slug: React.PropTypes.string.isRequired,
    title: React.PropTypes.string
  },
  getInitialState: function () {
    return {
      open: false,
      failed: false,
      timestamp: "never",
      tableState: {
        greyed: {},
        sort: -1,
        reverse: false
      }
    };
  },
  sortColumn: function (column) {
    if (this.state.tableState.sort === column) {
      this.setState({
        tableState: React.addons.update(this.state.tableState, {
          reverse: {
            $set: !this.state.tableState.reverse
          }
        })
      });
    } else {
      this.setState({
        tableState: React.addons.update(this.state.tableState, {
          sort: {
            $set: column
          },
          reverse: {
            $set: false
          }
        })
      });
    }
  },
  greyRow: function (item) {
    newkey = {};
    newkey[item] = !this.state.tableState.greyed[item];
    this.setState({
      tableState: React.addons.update(this.state.tableState, {
        greyed: {
          $merge: newkey
        }
      })
    });
  },
  resetTable: function () {
    this.setState({
      tableState: {
        greyed: {},
        sort: -1,
        reverse: false
      }
    });
  },
  handleClick: function () {
    if (this.state.open) {
      this.setState({
        open: false
      });
    } else {
      this.setState({
        open: true
      });
      if (!this.state.data) {
        this.loadData();
      }
    }
  },
  timestamp: function () {
    var now = new Date();
    return now.toLocaleTimeString();
  },
  loadData: function () {
    // remove any existing data, so we see a loading thing again
    this.setState({
      data: undefined
    });
    this.setState({
      has_items: false
    });
    this.setState({
      timestamp: "loading"
    });
    $j.get("scheduling_checks/" + this.props.slug).done(function (data) {
      var data_parse = JSON.parse(data);
      this.setState({
        data: data_parse,
        has_items: data_parse.body && data_parse.body.length > 0,
        failed: false,
        timestamp: this.timestamp()
      });
    }.bind(this)).fail(function (data) {
      this.setState({
        failed: true,
        timestamp: this.timestamp()
      });
    }.bind(this));
  },
  /*loads all of the scheduling checks */
  componentDidMount() {
    this.loadData();
  },
  render: function () {
    var body;
    if (this.state.failed) {
      body = /*#__PURE__*/React.createElement("div", {
        className: "placeholder load_fail"
      }, "(loaded ", this.state.timestamp, ", loading failed \u2639)");
    } else if (!this.state.open && this.state.timestamp == "never") {
      body = /*#__PURE__*/React.createElement("div", {
        className: "placeholder load_fail"
      }, "(loaded ", this.state.timestamp, ")");
    } else if (this.state.timestamp == "loading") {
      body = /*#__PURE__*/React.createElement("div", {
        className: "placeholder load_yellow"
      }, "loading...");
    } else if (!this.state.open) {
      body = /*#__PURE__*/React.createElement("div", {
        className: "placeholder load_ready"
      }, "(loaded ", this.state.timestamp, ")");
    } else if (!this.state.data) {
      body = /*#__PURE__*/React.createElement("div", {
        className: "placeholder load_yellow"
      }, "loading...");
    } else {
      var data = this.state.data;
      var table;
      if (data.headings.length == 0) {
        table = /*#__PURE__*/React.createElement(SelectTable, {
          rows: data.body,
          header: false,
          saveState: this.state.tableState,
          clickHeader: this.sortColumn,
          clickRow: this.greyRow
        });
      } else {
        var columns = [];
        for (i = 0; i < data.headings.length; i++) {
          if (data.headings[i]) {
            columns[i] = {
              key: String(i),
              label: data.headings[i]
            };
          } else {
            columns[i] = {
              key: String(i),
              label: "Date/Time"
            };
          }
        }
        table = /*#__PURE__*/React.createElement(SelectTable, {
          rows: data.body,
          columns: columns,
          header: true,
          saveState: this.state.tableState,
          clickHeader: this.sortColumn,
          clickRow: this.greyRow
        });
      }
      var helpText;
      if (data.help_text) {
        helpText = /*#__PURE__*/React.createElement("div", {
          className: "help-text"
        }, data.help_text);
      }
      body = /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
        className: "placeholder load_ready"
      }, "(loaded ", this.state.timestamp, ")"), /*#__PURE__*/React.createElement("div", {
        className: "alittlepspace"
      }), helpText, /*#__PURE__*/React.createElement("div", {
        className: "table-wrapper"
      }, table));
    }
    return /*#__PURE__*/React.createElement("div", {
      className: `scheduling-check ${this.state.has_items ? "items" : this.state.data ? "no-items" : "loading"}`
    }, /*#__PURE__*/React.createElement(ScheduleButton, {
      onClick: this.handleClick
    }), /*#__PURE__*/React.createElement(RefreshButton, {
      onClick: this.loadData
    }), /*#__PURE__*/React.createElement(ResetButton, {
      onClick: this.resetTable
    }), /*#__PURE__*/React.createElement("div", {
      className: "scheduling-check-title"
    }, /*#__PURE__*/React.createElement("span", {
      onClick: this.handleClick
    }, this.props.title)), /*#__PURE__*/React.createElement("div", {
      className: "scheduling-check-body"
    }, body));
  }
});

/**
 * A load button, which calls its onClick prop
 */
var ScheduleButton = React.createClass({
  displayName: "ScheduleButton",
  propTypes: {
    onClick: React.PropTypes.func.isRequired
  },
  render: function () {
    return /*#__PURE__*/React.createElement("button", {
      onClick: this.props.onClick,
      className: "reset-button"
    }, "Open/Close");
  }
});

/**
 * A refresh button, which calls its onClick prop
 */
var RefreshButton = React.createClass({
  displayName: "RefreshButton",
  propTypes: {
    onClick: React.PropTypes.func.isRequired
  },
  render: function () {
    return /*#__PURE__*/React.createElement("button", {
      onClick: this.props.onClick,
      className: "refresh-button"
    }, "Refresh");
  }
});

/**
 * Calls its onClick prop to reset table greying/sorting
 */
var ResetButton = React.createClass({
  displayName: "ResetButton",
  propTypes: {
    onClick: React.PropTypes.func.isRequired
  },
  render: function () {
    return /*#__PURE__*/React.createElement("button", {
      onClick: this.props.onClick,
      className: "reset-button"
    }, "Reset");
  }
});

// Modified from react-json-table example code.
var SelectTable = React.createClass({
  displayName: "SelectTable",
  propTypes: {
    rows: React.PropTypes.array.isRequired,
    saveState: React.PropTypes.shape({
      greyed: React.PropTypes.object.isRequired,
      sort: React.PropTypes.any.isRequired,
      reverse: React.PropTypes.bool.isRequired
    }).isRequired,
    header: React.PropTypes.bool.isRequired,
    columns: React.PropTypes.array,
    clickHeader: React.PropTypes.func.isRequired,
    clickRow: React.PropTypes.func.isRequired
  },
  getInitialState: function () {
    return {};
  },
  render: function () {
    // clone the rows
    items = this.props.rows.slice();
    items = _.sortBy(items, this.props.saveState.sort);
    if (this.props.saveState.reverse) items.reverse();
    return /*#__PURE__*/React.createElement(JsonTable, {
      rows: items,
      columns: this.props.columns,
      settings: this.getSettings(),
      onClickHeader: this.onClickHeader,
      onClickRow: this.onClickRow
    });
  },
  getSettings: function () {
    var me = this;
    // We will add some classes to the selected rows and cells
    return {
      headerClass: function (current, key) {
        if (me.props.saveState.sort == key) {
          if (me.props.saveState.reverse) {
            return current + ' headerSelected sortReversed';
          } else {
            return current + ' headerSelected';
          }
        } else {
          return current;
        }
      },
      rowClass: function (current, item) {
        if (me.props.saveState.greyed[item]) {
          return current + ' rowGreyed';
        } else {
          return current;
        }
      },
      header: this.props.header
    };
  },
  onClickHeader: function (e, column) {
    this.props.clickHeader(column);
  },
  onClickRow: function (e, item) {
    this.props.clickRow(item);
  }
});
