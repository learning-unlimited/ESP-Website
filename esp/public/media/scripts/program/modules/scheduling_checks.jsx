/**
 * List of scheduling checks.
 *
 * Should have individual SchedulingCheck elements as children.
 */
var SchedulingCheckList = React.createClass({
  render: function () {
    return <div className="scheduling-check-list">
      {this.props.children}
    </div>;
  },
});

/**
 * A single scheduling check.
 *
 * This might or might not be loaded yet; clicking the heading will load the
 * data from the server and expand it.
 */
var SchedulingCheck = React.createClass({
  propTypes: {
    slug: React.PropTypes.string.isRequired,
    title: React.PropTypes.string,
  },

  getInitialState: function () {
    return {
      open: false,
      failed: false,
      timestamp: "never",
    };
  },

  handleClick: function () {
    if (this.state.open) {
      this.setState({open: false})
    } else {
      this.setState({open: true});
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
    this.setState({data: undefined});

    $j.get("scheduling_checks/" + this.props.slug)
    .done(function (data) {
      this.setState({
        data: data,
        failed: false,
        timestamp: this.timestamp(),
      });
    }.bind(this))  
    .fail(function (data) {
      this.setState({
        failed: true,
        timestamp: this.timestamp(),
      });
    }.bind(this));
  },

  render: function () {
    var body;
    if (this.state.failed) {
      body = <div className="placeholder">
        (loaded {this.state.timestamp}, loading failed ☹)
      </div>;
    } else if (!this.state.open) {
      body = <div className="placeholder">
        (loaded {this.state.timestamp}, click title to open)
      </div>;
    } else if (!this.state.data) {
      body = <div className="placeholder">loading...</div>;
    } else {
      var data = JSON.parse(this.state.data); // Might not work on old browsers
      var table;
      if (data.headings.length == 0) {
        var settings = {
          header: false
        };
        /*var settings = {
          cellClass: function( current, key, item){
              return current + ' cell_' + key + item.age;
          },
          classPrefix: 'mytable',
          header: true,
          headerClass: function( current, key ){
            if( key == 'color')
              return current + ' imblue';
            return current;
          },
          keyField: 'name',
          noRowsMessage: 'Where are my rows?',
          rowClass: function( current, item ){
            return current + ' row_' + item.name;
          }
        };*/
        table = <JsonTable rows = {data.body} settings = {settings} />;
        // table = <JsonTable rows = {data.body} />;
      } else {
        var columns = [];
        for (i = 0; i < data.headings.length; i++) {
          if (!!data.headings[i]) {
            columns[i] = {key: String(i), label: data.headings[i]};
          } else {
            columns[i] = {key: String(i), label: " "};
          }
        }
        table = <JsonTable rows = {data.body} columns = {columns} />;
        //table = <JsonTable rows = {data.body} />;
      }
      body = <div>
        <div className="placeholder">
          (loaded {this.state.timestamp}, click title to close)
        </div>
        {table}
      </div>;
    }

    return <div className="scheduling-check">
      <div className="scheduling-check-title">
        <span onClick={this.handleClick}>{this.props.title}</span>
        <RefreshButton onClick={this.loadData} />
      </div>
      <div className="scheduling-check-body">
        {body}
      </div>
    </div>;
  },
});

/**
 * A refresh button, which calls its onClick prop
 */
var RefreshButton = React.createClass({
  propTypes: {
    onClick: React.PropTypes.func.isRequired,
  },

  render: function () {
    return <button onClick={this.props.onClick} className="refresh-button">
      ↻
    </button>;
  },
});
