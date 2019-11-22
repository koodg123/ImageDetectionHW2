import cv2
import glob
import json
import math
import numpy as np
import pickle
import time

import myhog

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from scipy.ndimage.measurements import label
from skimage.feature import hog
from sklearn.svm import LinearSVC
from sklearn.metrics import recall_score
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.utils import shuffle
from sklearn import svm
from sklearn.externals import joblib
from sklearn.model_selection import GridSearchCV

class WindowFinder(object):
    """Finds windows in an image that contain a car."""
    def __init__(self, cfgfilepath):

        ### Hyperparameters, if changed ->(load_saved = False) If
        ### the classifier is changes load_feaures can be True
        self.load_saved     = False# Loads classifier and scaler
        self.load_features  = False # Loads saved features (to train new classifier)

        self.spatial_size   = (8, 8)
        self.spatial_feat   = True # Spatial features on or off
        self.hist_feat      = False # Histogram features on or off
        self.hog_feat       = True # HOG features on or off

        # The locations of all the data.   
        # self.notred_data_folders = ['../data/fpt/not_red_shukai', '../data/fpt/not_red_signal', '../data/fpt/not_red_wall', '../data/fpt/not_red_wall2', '../data/not_red_from_itweek', '../data/notred_whiteblack']
        # self.red_data_folders = ['../data/red', '../data/red_close_gairan','../data/red_close_wall', '../data/fordate', '../data/fpt/red_shukai', '../data/fpt/red_shukai2']#'../data/fpt/red_not_pittiri', '../data/fpt/fpt_red_siro_wall'
        self.notred_data_folders = ['../data/fpt/not_red_shukai', '../data/fpt/not_red_signal', '../data/fpt/not_red_wall', '../data/fpt/not_red_wall2', '../data/not_red_from_itweek', '../data/notred_whiteblack']
        self.red_data_folders = ['../data/doll/bkc1']   
        self.clf_name = 'clf,p'
        self.scaler_name = 'scaler.p'
        
        ######Classifiers                            
        self.pred_thresh = 0.65 #Increase to decrease likelihood of detection.
        
        ###### Variable for Classifier and Feature Scaler ##########
        # self.untrained_clf = RandomForestClassifier(n_estimators=100, max_features = 2, min_samples_leaf = 4,max_depth = 25)
        tuned_parameters = [{'C': [0.1, 0.5, 1.0, 5.0, 10.0, 50.0, 100.0]}]
        # tuned_parameters = [{'C': [0.1]}]
        self.grid_search = GridSearchCV(svm.LinearSVC(max_iter = 1000000), tuned_parameters, cv=5)

        self.trained_clf, self.scaler = self.__get_classifier_and_scaler()

    def __get_classifier_and_scaler(self):
        """
        Gets the classifier and scaler needed for the rest of the operations. Loads from cache if 
        load_saved is set to true.
        """
        if self.load_saved:
            print('Loading saved classifier and scaler...')
            clf = pickle.load( open( "./cache/" + self.clf_name, "rb" ) )
            scaler = pickle.load(open( "./cache/" + self.scaler_name, "rb" ))
            print(clf.get_params())

            np.set_printoptions(suppress=True)	
            np.set_printoptions(precision=6, floatmode='fixed')
        else:
            # Split up data into randomized training and test sets
            print('Training...')
            rand_state = np.random.randint(0, 100)
            
            notred_features, red_features, filenames = self.__get_features()
            scaled_X, y, scaler = self.__get_scaled_X_y(notred_features, red_features)

            test_size = 0.05
            X_train, X_test, y_train, y_test = train_test_split(
                scaled_X, y, test_size=test_size, random_state=rand_state)

            gscv = self.grid_search
            # Check the training time for the SVC
            t=time.time()
            gscv.fit(X_train, y_train)
            t2 = time.time()
            print(round(t2-t, 2), 'Seconds to train CLF...')
            # Extract best estimator
            clf = gscv.best_estimator_
            print('Grid Search is finished, search result of  C =', clf.C)

            # Check the score of the SVC
            # preds = clf.predict_proba(X_test)
            # preds = clf.decision_function(X_test)
            preds = 1/(1+(np.exp(-1*clf.decision_function(X_test))))
            print(preds)
            #get filename
            test_filenames = shuffle(filenames, random_state=rand_state)[len(scaled_X) - len(preds):]
            print(len(test_filenames), len(preds))
            for i, proba in enumerate(preds):
                correct = False
                ans = -1
                ans_proba = 0
                if proba < 0.5:
                    ans = 0
                    ans_proba = (1.0-proba)*100.0
                else:
                    ans = 1
                    ans_proba = proba * 100.0
                if ans == y_test[i]:
                    correct = True
                if correct == False:
                    print('\033[31mproba = {}, predict = {}, correct = {}, testcase = {}\033[0m'.format(round(ans_proba, 3), ans, correct, test_filenames[i]))
                else:
                    print('proba = {}, predict = {}, correct = {}, testcase = {}'.format(round(ans_proba, 3), ans, correct, test_filenames[i]))
            # Check the prediction time for a single sample
            t=time.time()

            print('Pickling classifier and scaler...')
            pickle.dump( clf, open( "./cache/" + self.clf_name, "wb" ) )
            pickle.dump( scaler, open( "./cache/" + self.scaler_name, "wb" ) )

        return clf, scaler
           
    def __get_features(self):
        """
        Gets features either by loading them from cache, or by extracting them from the data.
        """   
        if self.load_features:
            print('Loading saved features...')
            notred_features, red_features, filenames = pickle.load( open( "./cache/features.p", "rb" ) )
            
        else: 
            # print("Extracting features from %s samples..." % self.sample_size)          
            print("Extracting features...")          

            notreds = []
            reds = []
            filenames = []

            for folder in self.notred_data_folders:
                image_paths =glob.glob(folder+'/*')
                for path in image_paths:
                    notreds.append(path)
            for folder in self.red_data_folders:
                image_paths =glob.glob(folder+'/*')
                for path in image_paths:
                    reds.append(path)

            filenames.extend(notreds)
            filenames.extend(reds)
            # notreds = notreds[0:self.sample_size]
            # reds =  reds[0:self.sample_size]


            start = time.clock()
            notred_features = self.__extract_features(notreds)
            red_features = self.__extract_features(reds)

            end = time.clock()
            print("Running time : %s seconds" % (end - start))
            
            print('Pickling features...')
            pickle.dump((notred_features, red_features, filenames), open( "./cache/features.p", "wb" ))
            
        return notred_features, red_features, filenames

    def __extract_features(self, imgs):
        """
        Extract features from image files.
        """
        
        # Create a list to append feature vectors to
        features = []
        # Iterate through the list of images
        for file in imgs:
            # Read in each one by one
            # image = mpimg.imread(file)
            image = cv2.imread(file)
            # Get features for one image
            file_features = self.__single_img_features(image)
            #Append to master list
            features.append(file_features)
        # Return list of feature vectors
        return features
   

    def __single_img_features(self, img):

        """
        Define a function to extract features from a single image window
        This function is very similar to extract_features()
        just for a single image rather than list of images
        Define a function to extract features from a single image window
        This function is very similar to extract_features()
        just for a single image rather than list of images
        """
        #1) Define an empty list to receive features
        img_features = []
        #2) Apply color conversion if other than 'RGB'

        # hls = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)# convert it to HLS
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
   
        #3) Compute spatial features if flag is set
        if self.spatial_feat == True:
            # spatial_hls = self.__bin_spatial(hls)
            spatial_rgb = self.__bin_spatial(img)
            spatial_hsv = cv2.cvtColor(spatial_rgb, cv2.COLOR_BGR2HSV)
            img_features.append(spatial_hsv.ravel()/256)
            img_features.append(spatial_rgb.ravel()/256)

        #7) Compute HOG features if flag is set
        if self.hog_feat == True:

            hog_features = self.__get_hog_features(gray)
            #8) Append features to list
            img_features.append(hog_features)

        #9) Return concatenated array of img_features
        return np.concatenate(img_features)

    def singleimgfeatures(self, img):
        return self.__single_img_features(img)

    def __get_scaled_X_y(self, notred_features, red_features):
        X = np.vstack((notred_features, red_features)).astype(np.float64)                        
        # Fit a per-column scaler
        X_scaler = StandardScaler().fit(X)
        # Apply the scaler to X
        scaled_X = X_scaler.transform(X)

        # Define the labels vector
        y = np.hstack((np.zeros(len(notred_features)), np.ones(len(red_features))))

        # Pickle scaler parameter
        mean = np.nanmean(np.array(X), axis=0)
        std = np.nanstd(np.array(X), axis=0)
        pickle.dump(mean, open( "./cache/scaler_mean.p", "wb"))
        pickle.dump(std, open( "./cache/scaler_std.p", "wb"))

        return scaled_X, y, X_scaler

    # Define a function to return HOG features and visualization
    def __get_hog_features(self, img, vis=False, feature_vec=True):
        return myhog.myhog(img)


    # Define a function to compute binned color features  
    def __bin_spatial(self, img):
        features = cv2.resize(img, self.spatial_size, cv2.INTER_LINEAR)
        return features

    # Define a function to compute color histogram features 
    # NEED TO CHANGE bins_range if reading .png files with mpimg!
    def __color_hist(self, img, bins_range=(0, 256)):
        channel1_hist = np.histogram(img[:,:,0], bins=[0, 21, 42, 64, 85,106, 128, 149, 170, 192, 213, 234, 256])
        channel2_hist = np.histogram(img[:,:,1], bins=[0, 21, 42, 64, 85,106, 128, 149, 170, 192, 213, 234, 256])
        channel3_hist = np.histogram(img[:,:,2], bins=[0, 21, 42, 64, 85,106, 128, 149, 170, 192, 213, 234, 256])
        hist_features = np.concatenate((channel1_hist[0], channel2_hist[0], channel3_hist[0]))
        return hist_features

    # Define a function to extract features from a list of images
    # Have this function call bin_spatial() and color_hist()
    def predictoneimage(self, img):
        test_image = cv2.resize(img, (64, 32), cv2.INTER_LINEAR)
        features = self.__single_img_features(test_image)
        test_features = self.scaler.transform(np.array(features).reshape(1, -1))
        bias = self.trained_clf.intercept_
        dot = np.dot(self.trained_clf.coef_[0], test_features[0]) 
        rst = dot + bias
        sigmoided_rst = 1/(1+np.exp(-1*rst))
        print(dot.shape)
        print("rst:", rst, "sigmoid:", sigmoided_rst)
        # prediction = self.trained_clf.predict_proba(test_features)[:,1]
        prediction = 1/(1+(np.exp(-1*self.trained_clf.decision_function(test_features))))
        print(prediction)
        return prediction
