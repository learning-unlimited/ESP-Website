// Global configuration variables normally injected by Django templates.
// These stubs allow the test suite to run without the production page context.
var contiguous_tolerance = "0";
var has_moderator_module = "False";
var has_autoscheduler_frontend = "False";
var prog_id = "TestProgram/2020";

function generateFakeMatrix(){
    var sections = new Sections(section_fixture(),
                                 {},
                                 {},
                                 teacher_fixture(),
                                 {},
                                 schedule_assignment_fixture(),
                                 new ApiClient());
    var messagePanel = new MessagePanel($j("<div>"),
                                         "Welcome to the Ajax Scheduler!");
    var sectionInfoPanel = new SectionInfoPanel($j("<div>"),
                                                 sections,
                                                 messagePanel)
    var matrix = new Matrix(new Timeslots(time_fixture()),
                  room_fixture(),
                  {},
                  sections,
                  $j("<div>"),
                  messagePanel,
                  sectionInfoPanel);
    matrix.getTable = function() {
        return this.el.find(".ft_scroller table")[0];
    }
    matrix.render();
    return matrix;

}
