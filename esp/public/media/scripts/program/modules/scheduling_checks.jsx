/** @jsx React.DOM */

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

  loadData: function () {
    // remove any existing data, so we see a loading thing again
    this.setState({data: undefined});

    $j.get("scheduling_checks/" + this.props.slug)
    .done(function (data) {
      this.setState({
        data: data,
        failed: false,
      });
    }.bind(this))  
    .fail(function (data) {
      this.setState({failed: true});
    }.bind(this));
  },

  render: function () {
    var body;
    if (!this.state.open) {
      body = <div className="placeholder">(click title to open)</div>;
    } else if (this.state.failed) {
      body = <div className="placeholder">loading failed :(</div>;
    } else if (!this.state.data) {
      body = <div className="placeholder">loading...</div>;
    } else {
      body = <div className="data" dangerouslySetInnerHTML={{__html: this.state.data}} />;
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
