// Inject difficulty data from the tag to support custom difficulties
const DIFFICULTIES = INJECTED_DIFFICULTIES !== "None" 
    ? JSON.parse(INJECTED_DIFFICULTIES)
    : [
        ["*", "This Shouldn't Appear!"],
        ["**", "This Shouldn't Appear!"],
        ["***", "This Shouldn't Appear!"],
        ["****", "This Shouldn't Appear!"]
    ];

const MODIFIED_COLOR = "#0066ff22";

const FILTER_IDS = ["grade_filter", "difficulty_filter", "status_filter", "duration_filter"];

/**
    Converts from hours to a formatted duration (eg. "0.05" -> "3 mins", "1.5" -> "1 hour 30 mins")
    @param {string} numString - a duration as a float in a string (eg. "0.05")
    @returns {string} the formatted time (eg. "1 hour 30 mins")
*/
function floatToFormattedTime(numString) {
    let float = Number(numString);
    let result = "";
    if (Math.floor(float) >= 1) {
        result += `${Math.floor(float)} hrs`;
    }
    if (float - Math.floor(float) > 0.01) {
        result += ` ${Math.round((float - Math.floor(float))*60)} mins`;
    }
    return result;
}

function hideClass(cls) {
    $j(cls).hide();
}

function showClass(cls) {
    $j(cls).show();
}

// Filters for the different pieces of class information. Each of these returns a predicate
// which returns true if the class matches the filter passed to the parent function.

function gradeFilter(grade) {
    return cls => grade === "all" || cls.classList.contains(`grade_${grade}`);
}

function difficultyFilter(difficulty) {
    return cls => difficulty === "all" || cls.getAttribute("data-difficulty") === difficulty;
}

function durationFilter(duration) {
    return cls => duration === "all" || cls.getAttribute("data-duration") === duration;
}

function openFilter(status) {
    return cls => {
        return status === "all" ||
        (status === "closed" && cls.getAttribute("data-is-closed") === "True") || 
        (status === "open" && cls.getAttribute("data-is-closed") === "False");
    }
}

function applyCurrentFilters() {
    applyFilters(getOptions())
    updateEmptyCategories();
}

function applyFilters({grade, difficulty, status, duration}) {
    let classes = Array.from(document.getElementsByClassName("show_class"));
    let shownClasses = classes
        .filter(gradeFilter(grade))
        .filter(difficultyFilter(difficulty))
        .filter(openFilter(status))
        .filter(durationFilter(duration));

    classes.forEach(hideClass);
    shownClasses.forEach(showClass);
}

function getOptions() {
    return {
        grade: document.getElementById("grade_filter").value,
        difficulty: document.getElementById("difficulty_filter").value,
        status: document.getElementById("status_filter").value,
        duration: document.getElementById("duration_filter").value,
    }
}

function updateEmptyCategories() {
    $j(".cat_wrapper").each(function() {
       if ($j(this).children("div").filter(function() { return $j(this).css("display") != "none" }).length == 0) {
           if (hide_empty_cats) {
               $j(this).hide();
               $j("a[data-category=" + $j(this).data("category") + "]").attr('disabled', true).addClass('disabled');
           }
       } else {
           $j(this).show();
           $j("a[data-category=" + $j(this).data("category") + "]").attr('disabled', false).removeClass('disabled');
       }
    });
}

var student_grade = esp_user.cur_grade;
if (student_grade != "" && student_grade != null) {
    student_grade = parseInt(student_grade);
    const gradeFilterElem = document.getElementById("grade_filter")
    if (gradeFilterElem.querySelector(`option[value="${student_grade}"]`)) {
        gradeFilterElem.value = student_grade
    }
}

applyCurrentFilters()

// Set up duration options by finding all unique durations from the classes in the catalog
const durationFilterElem = document.getElementById("duration_filter");
let uniqueLengths = [
        // Convert to and back from a Set to keep only unique values
        ...new Set(
            Array.from(document.getElementsByClassName("show_class"))
                .map(cls=>cls.getAttribute("data-duration"))
        )
    ]
    .sort((a,b)=>a-b) // least to greatest
    .map((val)=>[val, floatToFormattedTime(val)])
    .forEach(([raw, formatted])=>{
        let option = document.createElement("option")
        option.setAttribute("value", raw)
        option.textContent = formatted
        durationFilterElem.append(option)
    });

// Set up difficulties by getting them from tag data (injected further up)
const difficultyFilterElem = document.getElementById("difficulty_filter");

DIFFICULTIES.forEach(([difficulty])=>{
    let option = document.createElement("option")
    option.setAttribute("value", difficulty)
    option.textContent = difficulty
    difficultyFilterElem.append(option)
});

function setModifiedColor(selectElem) {
    if (selectElem.value !== "all") {
        selectElem.style.background = MODIFIED_COLOR;
    } else {
        selectElem.style.background = "";
    }
}

FILTER_IDS.forEach((id)=>{
    const filterElem = document.getElementById(id)
    // Covers the case when a page refresh has preserved form values
    // or the grade is automatically set.
    setModifiedColor(filterElem);

    filterElem.addEventListener("change", ()=>{
        setModifiedColor(filterElem)
        applyCurrentFilters()
    });
})

function configure_addbuttons()
{
    if (register_from_catalog) {
        //  Registration from the catalog is allowed
        $j("input.addbutton").show();
    }
}
function topFunction() 
{ 
    document.body.scrollTop = 0; // For Safari 
    document.documentElement.scrollTop = 0; // For Chrome, Firefox, IE and Opera 
} 
     
window.onscroll = function() {scrollFunction()}; 
     
function scrollFunction() { 
    if (document.body.scrollTop > 100 || document.documentElement.scrollTop > 100) { 
        document.getElementById("topBtn").style.display = "block"; 
        document.getElementById("topBtn").style.position = "fixed";
        document.getElementById("topBtn").style.bottom = "20px";
    } else { 
        document.getElementById("topBtn").style.display = "none"; 
    } 
} 

$j(document).ready(configure_addbuttons);
