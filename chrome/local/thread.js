function Task(name, delay, exec) {
	// overwrite this function
	this.exec = exec || function (task, resolve) { resolve(); };
	this.name = name;
	this.delay = delay || 0;
}

function Thread() {
	this.tasks = [];
	this.id = 0;
	this.curTask = null;
	this.curTaskBeginTime = 0;
}

Thread.prototype.start = function(intervalTime) {
	if (this.id != 0) {
		return;
	}
	let thiz = this;
	function wrapRun() {
		thiz._run();
	}
	this.curTaskBeginTime = Date.now();
	intervalTime = intervalTime || 300;
	this.id = setInterval(wrapRun, intervalTime);
}

Thread.prototype.pause = function() {
	
}

Thread.prototype._run = function() {
	if (this.curTask != null) {
		return;
	}
	if (this.tasks.length == 0) {
		return;
	}
	let topTask = this.tasks[0];
	let diffTime = Date.now() - this.curTaskBeginTime;
	if (diffTime < topTask.delay) {
		// console.log('Wait...');
		// wait
		return;
	}
	this.curTask = this.tasks.shift();
	let thiz = this;
	function _resolve_() {
		thiz._resolve();
	}
	// console.log('Thread.run ', this.curTask);
	this.curTask.exec(this.curTask, _resolve_);
}

Thread.prototype._resolve = function() {
	this.curTask = null;
	this.curTaskBeginTime = Date.now();
}

Thread.prototype.stop = function() {
	clearInterval(this.id);
	this.id = 0;
	this.curTask = null;
	this.curTaskBeginTime = 0;
}

// exec: function(resolve, reject) 
// when finish call resolve() or reject()
Thread.prototype.addTask = function(task) {
	this.tasks.push(task);
}

Thread.prototype.insertTask = function (idx, task) {
	this.tasks.splice(idx, 0, task);
}

Thread.prototype.addUniqueTask = function(uniqueId, task) {
	for (let i = 0; i < this.tasks.length; i++) {
		let tk = this.tasks[i];
		if (tk['__unique_id__'] && tk['__unique_id__'] == uniqueId) {
			return;
		}
	}
	if (uniqueId != null) {
		task['__unique_id__'] = uniqueId;
	}
	
	this.tasks.push(task);
}

class ThreadPool {
	constructor(size = 10) {
		this.pools = [];
		this.tasks = [];
		for (let i = 0; i < size; i++) {
			this.pools.push(new Thread());
			// share tasks queue
			this.pools[i].tasks = this.tasks;
		}
	}

	start() {
		for (let t of this.pools) {
			t.start();
		}
	}

	addTask(task) {
		this.tasks.push(task);
	}
}

